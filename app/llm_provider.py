import json
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LLMProvider:
    def __init__(self, provider=None, model=None):
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "gemini")).lower()
        self.model = model or os.environ.get("LLM_MODEL", "llama3.2:latest")

        if self.provider == "ollama":
            self.host = os.environ.get("OLLAMA_HOST", "")
            self.ssh_host = os.environ.get("OLLAMA_SSH_HOST", "")
            self.ssh_port = int(os.environ.get("OLLAMA_SSH_PORT", "2222"))
            self.ssh_user = os.environ.get("OLLAMA_SSH_USER", "User")
            self.ssh_pass = os.environ.get("OLLAMA_SSH_PASS", "mth123")
            self._ssh_client = None

    def _ensure_ssh(self):
        if self._ssh_client and self._ssh_client.get_transport() and self._ssh_client.get_transport().is_active():
            return
        import paramiko
        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        host = self.ssh_host or self.host.split(":")[0]
        self._ssh_client.connect(host, port=self.ssh_port, username=self.ssh_user,
                                 password=self.ssh_pass, timeout=10)

    def _ollama_api(self, endpoint, data=None):
        self._ensure_ssh()
        import random, io
        if data:
            body = json.dumps(data)
            rand = random.randint(1000, 9999)
            tmp = f"C:\\Users\\User\\AppData\\Local\\Temp\\ollama_{rand}.json"
            # Write body file via SFTP (same SSH connection)
            with self._ssh_client.open_sftp() as sftp:
                with sftp.open(tmp, 'w') as f:
                    f.write(body)
            cmd = f'curl -s -m 120 http://localhost:11434/api/{endpoint} -d @"{tmp}"'
            stdin, stdout, stderr = self._ssh_client.exec_command(cmd, timeout=180)
            out = stdout.read().decode()
            err = stderr.read().decode().strip()
            if err:
                raise RuntimeError(f"Ollama SSH error: {err}")
            return json.loads(out) if out else {}
        else:
            stdin, stdout, stderr = self._ssh_client.exec_command(
                f'curl -s http://localhost:11434/api/{endpoint}'
            )
            out = stdout.read().decode()
            return json.loads(out) if out else {}

    def generate(self, prompt, temperature=0.3, system_prompt=None):
        if self.provider == "ollama":
            return self._ollama_generate(prompt, temperature)
        elif self.provider == "openrouter":
            return self._openrouter_generate(prompt, temperature, system_prompt)
        raise ValueError(f"Unknown provider: {self.provider}")

    def _ollama_generate(self, prompt, temperature=0.3):
        result = self._ollama_api("generate", {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
            "options": {"num_predict": 2048},
        })
        return result.get("response", "")

    def _openrouter_generate(self, prompt, temperature=0.3, system_prompt=None):
        import requests
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY tidak ditemukan di environment")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 4096,
            },
            timeout=120,
        )
        if resp.status_code == 429:
            raise RuntimeError("OPENROUTER_RATE_LIMITED")
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def chat(self, messages, temperature=0.3):
        if self.provider == "ollama":
            result = self._ollama_api("chat", {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "temperature": temperature,
            })
            return result.get("message", {}).get("content", "")
        elif self.provider == "openrouter":
            return self._openrouter_generate(
                messages[-1]["content"] if messages else "",
                temperature,
                messages[0]["content"] if messages and messages[0]["role"] == "system" else None
            )
        raise ValueError(f"Unknown provider: {self.provider}")
