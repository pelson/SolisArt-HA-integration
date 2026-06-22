from dataclasses import dataclass

_VALID_MODES = {"local", "cloud", "fallback"}

@dataclass(frozen=True)
class EndpointStrategy:
    mode: str
    local_url: str | None
    cloud_url: str | None

    def candidates(self) -> list[str]:
        if self.mode not in _VALID_MODES:
            raise ValueError(f"unknown mode: {self.mode}")
        if self.mode == "local":
            if not self.local_url:
                raise ValueError("local mode requires local_url")
            return [self.local_url]
        if self.mode == "cloud":
            if not self.cloud_url:
                raise ValueError("cloud mode requires cloud_url")
            return [self.cloud_url]
        urls = [u for u in (self.local_url, self.cloud_url) if u]
        if not urls:
            raise ValueError("fallback mode requires at least one URL")
        return urls
