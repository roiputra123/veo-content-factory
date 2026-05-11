import os
import yaml

_NICHES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "niches")

class NicheLoader:
    def __init__(self, niches_dir=None):
        self.niches_dir = niches_dir or _NICHES_DIR
        self._cache = {}

    def list_niches(self):
        if not os.path.isdir(self.niches_dir):
            return []
        files = sorted(f for f in os.listdir(self.niches_dir) if f.endswith(".yaml"))
        return [f.replace(".yaml", "") for f in files]

    def list_niche_names(self):
        niches = []
        for slug in self.list_niches():
            profile = self.load(slug)
            if profile:
                niches.append({"slug": slug, "name": profile.get("name", slug), "description": profile.get("description", "")})
        return niches

    def load(self, slug):
        if slug in self._cache:
            return self._cache[slug]
        path = os.path.join(self.niches_dir, f"{slug}.yaml")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            profile = yaml.safe_load(f)
        self._cache[slug] = profile
        return profile

    def get_defaults(self, slug, component=None):
        profile = self.load(slug)
        if not profile:
            return {}
        if component:
            return profile.get(component, {})
        return profile
