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

    def generate(self, prompt, temperature=0.3):
        if self.provider == "ollama":
            return self._ollama_generate(prompt, temperature)
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

    def chat(self, messages, temperature=0.3):
        if self.provider == "ollama":
            result = self._ollama_api("chat", {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "temperature": temperature,
            })
            return result.get("message", {}).get("content", "")
        raise ValueError(f"Unknown provider: {self.provider}")
