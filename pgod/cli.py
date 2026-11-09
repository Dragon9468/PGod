import asyncio
import time
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pgod.core.orchestrator import PresenceOrchestrator
from pgod.models import DeviceReplacementRequest

app = typer.Typer(
    name="pgod",
    help="👁️ PGOD: Autonomous Ambient Presence Guardian & Zero-Friction Proof-of-Life Daemon.",
    add_completion=False,
)
console = Console(highlight=False)


@app.command("status")
def status_cmd():
    """👁️ Xem trang thai he thong giam sat su song PGod va danh sach thiet bi tin cay."""
    orchestrator = PresenceOrchestrator()
    devices = orchestrator.device_sensor.devices

    table = Table(title="📱 Danh Sách Thiết Bị Của Người Sáng Lập (Trusted Devices)", show_header=True, header_style="bold cyan")
    table.add_column("Mã Thiết Bị", style="bold yellow", width=24)
    table.add_column("Tên Thiết Bị", style="cyan", width=28)
    table.add_column("Loại", style="white", width=14)
    table.add_column("Tọa Độ Cuối", style="magenta", width=22)
    table.add_column("Trạng Thái", style="bold green")

    for d in devices.values():
        coord = f"{d.last_latitude}, {d.last_longitude}" if d.last_latitude else "N/A"
        badge = "[bold green]ACTIVE[/]" if d.status.value == "ACTIVE" else f"[dim red]{d.status.value}[/]"
        table.add_row(d.device_id, d.device_name, d.device_type, coord, badge)
    console.print(table)


@app.command("verify")
def verify_cmd(
    text: Optional[str] = typer.Option(None, "--text", "-t", help="Mẫu văn bản / câu hỏi / prompt vừa gõ"),
    planet_url: str = typer.Option("http://localhost:8000", "--planet-url", help="Địa chỉ Planet PGDSecurity"),
    no_dispatch: bool = typer.Option(False, "--no-dispatch", help="Chỉ đánh giá độ tin cậy, không gửi heartbeat reset timer"),
):
    """🔍 Thực hiện thẩm định sự sống đa phương thức tức thì (Stylometry + Biometrics + GPS)."""
    orchestrator = PresenceOrchestrator()
    console.print("[bold cyan]Đang thu thập tín hiệu sự sống thụ động từ các cảm biến...[/]")

    sample = text or "Theo tôi hệ thống cần tự tiến hóa và ưu tiên hạ tầng trong nước."
    report = orchestrator.evaluate_ambient_presence(
        text_sample=sample,
        auto_dispatch=not no_dispatch,
        planet_url=planet_url,
    )

    verdict_color = "bold green" if report.is_creator_verified else "bold red"
    console.print(Panel(
        f"[{verdict_color}]KẾT LUẬN THẨM ĐỊNH:[/] {'XÁC THỰC CHÍNH CHỦ (CREATOR VERIFIED)' if report.is_creator_verified else 'CHƯA ĐỦ ĐỘ TIN CẬY'}\n"
        f"[bold yellow]Độ Tin Cậy Tổng Hợp:[/] {report.composite_confidence}%\n"
        f"[cyan]Thời điểm đánh giá:[/] {report.evaluated_at}\n"
        f"[magenta]Gửi Heartbeat gia hạn:[/] {'ĐÃ GỬI TỰ ĐỘNG' if report.heartbeat_dispatched else 'CHƯA GỬI'}\n"
        f"[white]Chi tiết kết quả:[/] {report.dispatch_result or 'Chế độ đánh giá nội bộ'}",
        title="👁️ PGod Ambient Liveness Report"
    ))

    table = Table(title="Chi Tiết Tín Hiệu Các Cảm Biến", show_header=True, header_style="bold magenta")
    table.add_column("Cảm Biến", style="bold yellow", width=20)
    table.add_column("Điểm Tin Cậy", style="cyan", width=14)
    table.add_column("Tóm Tắt Nhận Định", style="white")

    for s in report.signals:
        table.add_row(s.sensor_type.value, f"{s.confidence_score}%", s.summary)
    console.print(table)


@app.command("replace-device")
def replace_device_cmd(
    old_id: str = typer.Argument(..., help="Mã thiết bị cũ bị hỏng (ví dụ: dev-phone-primary-01)"),
    new_id: str = typer.Argument(..., help="Mã thiết bị thay thế mới (ví dụ: dev-phone-new-galaxy)"),
    new_name: str = typer.Argument(..., help="Tên thiết bị mới (ví dụ: Creator New Phone)"),
    recovery_seed: str = typer.Option("SOVEREIGN_MASTER_RECOVERY_SEED_001", "--seed", help="Master Recovery Seed để chứng thực đổi máy"),
):
    """🔄 Giao thức đổi thiết bị: Thay điện thoại hỏng đột ngột mà không làm gián đoạn giám sát."""
    import hashlib
    orchestrator = PresenceOrchestrator()
    seed_hash = hashlib.sha256(recovery_seed.encode("utf-8")).hexdigest()

    req = DeviceReplacementRequest(
        old_device_id=old_id,
        new_device_id=new_id,
        new_device_name=new_name,
        recovery_seed_hash=seed_hash,
    )

    res = orchestrator.device_sensor.execute_device_replacement(req)
    if res.get("success"):
        console.print(Panel(
            f"[bold green]✔ ĐÃ THAY ĐỔI THIẾT BỊ THÀNH CÔNG[/]\n"
            f"[white]{res.get('message')}[/]\n"
            f"[cyan]Thiết bị mới đang hoạt động:[/] {res.get('active_device_id')}\n"
            f"[yellow]Thiết bị cũ '{old_id}' đã chuyển sang trạng thái REPLACED.[/]",
            title="📱 Device Replacement Completed"
        ))
    else:
        console.print(f"[bold red]❌ Lỗi thay đổi thiết bị:[/] {res.get('reason')}")


@app.command("daemon")
def daemon_cmd(
    interval_seconds: int = typer.Option(3600, "--interval", "-i", help="Chu kỳ kiểm tra thụ động (mặc định: 1 giờ)"),
    planet_url: str = typer.Option("http://localhost:8000", "--planet-url", help="Địa chỉ Planet PGDSecurity"),
):
    """🚀 Chạy PGod Daemon nền: Liên tục lắng nghe sự hiện diện và tự động reset timer 90 ngày."""
    orchestrator = PresenceOrchestrator()
    console.print(f"[bold green]🚀 PGod Ambient Guardian Daemon đã khởi động (Chu kỳ: {interval_seconds}s)...[/]")

    try:
        while True:
            report = orchestrator.evaluate_ambient_presence(planet_url=planet_url, auto_dispatch=True)
            console.print(f"[{datetime.now().strftime('%H:%M:%S')}] Kiểm tra thụ động: Độ tin cậy {report.composite_confidence}% | Gửi reset: {report.heartbeat_dispatched}")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        console.print("\n[yellow]Đã dừng PGod Daemon an toàn.[/]")


def main():
    app()


if __name__ == "__main__":
    main()

