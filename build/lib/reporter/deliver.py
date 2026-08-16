"""Report file writing + summary delivery via growthkit.channels."""
from pathlib import Path

from growthkit import channels as kit_channels


def write_report(md: str, cfg: dict, week_start: str) -> Path:
    d = Path(cfg["report_dir"]).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"growth-report-{week_start}.md"
    path.write_text(md)
    return path


def send_summary(text: str, cfg: dict, report_path: Path | None = None) -> list[str]:
    footer = f"\n\nFull report: {report_path}" if report_path else ""
    return kit_channels.send(text + footer, cfg["channels"])
