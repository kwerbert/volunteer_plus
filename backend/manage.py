#!/usr/bin/env python3
"""
Volunteer+ — единый CLI для управления микросервисами.

Запуск (из директории backend/):
    python manage.py run     [service ...]   # запустить сервисы (все, если не указаны)
    python manage.py stop    [service ...]   # остановить сервисы
    python manage.py restart [service ...]   # перезапустить
    python manage.py status  [service ...]   # быстрый статус (по PID/порту)
    python manage.py health  [service ...]   # health-check через /health
    python manage.py logs    [service ...]   # tail -f логов
    python manage.py seed                    # наполнить БД тестовыми данными

Имена сервисов можно указывать полностью (user_service) или сокращённо (user),
если сокращение однозначно. Без аргументов команда применяется ко всем сервисам.

Скрипт сам находит виртуальное окружение (.venv или venv) в backend/ или
в родительской директории. Для команд run/seed venv обязателен.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable
from urllib import request as urlrequest
from urllib.error import URLError

# =============================================================================
# CONSTANTS
# =============================================================================

PROJECT_DIR = Path(__file__).resolve().parent
PID_DIR = PROJECT_DIR / ".pids"
LOG_DIR = PROJECT_DIR / ".logs"
SELF = Path(__file__).resolve()

# (name, port). Порядок важен — сервисы запускаются в этом порядке.
SERVICES: list[tuple[str, int]] = [
    ("feed_service", 8001),
    ("subscription_service", 8002),
    ("event_service", 8003),
    ("organization_service", 8004),
    ("analytics_service", 8005),
    ("notification_service", 8006),
    ("chat_service", 8007),
    ("user_service", 8008),
]

# ANSI-цвета (не мешают, если терминал их не понимает)
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
GRAY = "\033[0;90m"
NC = "\033[0m"


# =============================================================================
# COMMON HELPERS
# =============================================================================

def _resolve_services(names: Iterable[str]) -> list[tuple[str, int]]:
    """Сопоставить пользовательские имена сервисов полному списку.

    Правила:
      - без имён → все сервисы;
      - точное совпадение имени → этот сервис;
      - иначе однозначное вхождение подстроки (user → user_service);
      - иначе предупреждение и пропуск.
    """
    names = list(names)
    if not names:
        return list(SERVICES)

    resolved: list[tuple[str, int]] = []
    seen: set[str] = set()

    for name in names:
        exact = next((s for s in SERVICES if s[0] == name), None)
        if exact is not None:
            if exact[0] not in seen:
                resolved.append(exact)
                seen.add(exact[0])
            continue

        matches = [s for s in SERVICES if name in s[0]]
        if len(matches) == 1:
            if matches[0][0] not in seen:
                resolved.append(matches[0])
                seen.add(matches[0][0])
        elif not matches:
            print(f"{YELLOW}⚠  Неизвестный сервис: {name}{NC}")
        else:
            print(f"{YELLOW}⚠  Неоднозначно '{name}': "
                  f"{[m[0] for m in matches]}{NC}")

    return resolved


def _python_exe_for(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _find_venv() -> Path | None:
    """Ищем виртуальное окружение в backend/ и на уровень выше."""
    candidates = [
        PROJECT_DIR / ".venv",
        PROJECT_DIR / "venv",
        PROJECT_DIR.parent / ".venv",
        PROJECT_DIR.parent / "venv",
    ]
    for c in candidates:
        if _python_exe_for(c).is_file():
            return c
    return None


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.4) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def _pid_on_port(port: int) -> int | None:
    """Best-effort: PID процесса, слушающего порт (lsof/ss на *nix, netstat на Windows)."""
    if sys.platform == "win32":
        try:
            res = subprocess.run(
                ["netstat", "-ano", "-p", "TCP"],
                capture_output=True, text=True, timeout=5,
            )
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3] == "LISTENING":
                    try:
                        return int(parts[4])
                    except ValueError:
                        continue
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None

    # lsof
    for cmd in (
        ["lsof", "-ti", f":{port}"],
        ["lsof", "-tiTCP:%d" % port, "-sTCP:LISTEN"],
    ):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                first = res.stdout.strip().splitlines()[0]
                try:
                    return int(first)
                except ValueError:
                    pass
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    # ss (Linux)
    try:
        res = subprocess.run(
            ["ss", "-ltnp", f"sport = :{port}"],
            capture_output=True, text=True, timeout=3,
        )
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                if f":{port}" not in line or "pid=" not in line:
                    continue
                chunk = line.split("pid=", 1)[1]
                pid_str = chunk.split(",", 1)[0].strip()
                try:
                    return int(pid_str)
                except ValueError:
                    continue
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _kill_pid(pid: int, timeout: float = 3.0) -> bool:
    """SIGTERM → wait → SIGKILL. True если процесс остановлен."""
    if not _is_process_alive(pid):
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _is_process_alive(pid):
            return True
        time.sleep(0.2)

    try:
        if sys.platform == "win32":
            os.kill(pid, signal.SIGTERM)  # на Windows это TerminateProcess
        else:
            os.kill(pid, signal.SIGKILL)
    except OSError:
        pass

    time.sleep(0.2)
    return not _is_process_alive(pid)


def _ask_yes_no(question: str) -> bool:
    try:
        answer = input(question + " (y/n): ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes", "д", "да")


def _tail_lines(path: Path, n: int) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.readlines()[-n:]
    except OSError:
        return []


def _read_pid_file(pid_file: Path) -> int | None:
    if not pid_file.is_file():
        return None
    try:
        return int(pid_file.read_text().strip())
    except (ValueError, OSError):
        return None


def _ensure_venv_or_reexec() -> bool:
    """Если мы не в venv, но venv есть — перезапускаемся через него.

    Возвращает True, если можно продолжать работу в текущем процессе.
    False — если venv не найден (и мы уже напечатали ошибку).
    """
    venv = _find_venv()
    if venv is None:
        print(f"{RED}❌ Виртуальное окружение не найдено!{NC}")
        print(f"   Искали в: {PROJECT_DIR} и {PROJECT_DIR.parent}")
        print("   Создайте: python -m venv .venv")
        return False

    venv_python = _python_exe_for(venv)
    try:
        same = Path(sys.executable).resolve() == venv_python.resolve()
    except OSError:
        same = False

    if same:
        return True

    # Перезапуск через venv-python. execv не возвращается.
    sys.stdout.flush()
    sys.stderr.flush()
    os.execv(
        str(venv_python),
        [str(venv_python), str(SELF), *sys.argv[1:]],
    )
    return False  # на случай, если execv каким-то чудом вернётся


# =============================================================================
# RUN / STOP / RESTART
# =============================================================================

def cmd_run(args: argparse.Namespace) -> int:
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}🚀  Запуск микросервисов Volunteer+{NC}")
    print(f"{BLUE}========================================{NC}")

    venv = _find_venv()
    if venv is None:
        print(f"{RED}❌ Виртуальное окружение не найдено!{NC}")
        print(f"   Искали в: {PROJECT_DIR} и {PROJECT_DIR.parent}")
        print("   Создайте: python -m venv .venv")
        return 1
    python_exe = _python_exe_for(venv)
    print(f"  📁 Venv:   {GREEN}{venv}{NC}")
    print(f"  🐍 Python: {python_exe}")

    PID_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

    # Проверка БД (только если запускаем user_service или всё)
    targets = _resolve_services(args.services)
    targets_names = {name for name, _ in targets}
    need_seed = False
    if "user_service" in targets_names and not (PROJECT_DIR / "users.db").is_file():
        need_seed = True
    if not (PROJECT_DIR / "volunteer_plus.db").is_file():
        need_seed = True

    if need_seed:
        print(f"{YELLOW}⚠️  Базы данных не найдены!{NC}")
        if _ask_yes_no("🌱 Запустить seed?"):
            rc = subprocess.run(
                [sys.executable, str(SELF), "seed"],
                cwd=str(PROJECT_DIR),
            ).returncode
            if rc != 0:
                print(f"{RED}❌ Seed завершился с ошибкой (код {rc}){NC}")
                return 1
        else:
            print(f"{RED}❌ Запуск отменён{NC}")
            return 1

    started = failed = skipped = 0

    print()
    print(f"{YELLOW}📍 Запуск сервисов:{NC}")
    print("  " + "-" * 44)

    for service, port in targets:
        service_dir = PROJECT_DIR / "app" / "services" / service
        pid_file = PID_DIR / f"{service}.pid"
        log_file = LOG_DIR / f"{service}.log"

        if not service_dir.is_dir():
            print(f"  {service:<25} {port:<8} {GRAY}⊘ НЕ СУЩЕСТВУЕТ{NC}")
            skipped += 1
            continue
        if not (service_dir / "main.py").is_file():
            print(f"  {service:<25} {port:<8} {GRAY}⊘ НЕТ main.py{NC}")
            skipped += 1
            continue

        # Уже запущен?
        pid = _read_pid_file(pid_file)
        if pid is not None and _is_process_alive(pid):
            print(f"  {service:<25} {port:<8} {YELLOW}⏭  УЖЕ ЗАПУЩЕН{NC} (PID: {pid})")
            continue
        if pid_file.is_file():
            pid_file.unlink(missing_ok=True)

        # Порт занят?
        if _is_port_open(port):
            print(f"  {service:<25} {port:<8} {RED}❌ ПОРТ ЗАНЯТ{NC}")
            failed += 1
            continue

        # Среда для дочернего процесса
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_DIR) + os.pathsep + env.get("PYTHONPATH", "")

        popen_kwargs: dict = {
            "cwd": str(PROJECT_DIR),
            "env": env,
            "stdout": None,
            "stderr": subprocess.STDOUT,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            popen_kwargs["start_new_session"] = True

        try:
            with log_file.open("w", encoding="utf-8") as lf:
                popen_kwargs["stdout"] = lf
                proc = subprocess.Popen(
                    [str(python_exe), "-m", f"app.services.{service}.main"],
                    **popen_kwargs,
                )
        except OSError as e:
            print(f"  {service:<25} {port:<8} {RED}✗ ОШИБКА: {e}{NC}")
            failed += 1
            continue

        pid_file.write_text(str(proc.pid))

        time.sleep(3)
        if proc.poll() is None:
            print(f"  {service:<25} {port:<8} {GREEN}✓ ЗАПУЩЕН{NC} (PID: {proc.pid})")
            started += 1
        else:
            print(f"  {service:<25} {port:<8} {RED}✗ ОШИБКА ЗАПУСКА{NC}")
            for line in _tail_lines(log_file, 5):
                print(f"      {line.rstrip()}")
            failed += 1
            pid_file.unlink(missing_ok=True)

    print("  " + "-" * 44)
    print(
        f"{BLUE}Запущено:{NC} {GREEN}{started}{NC} | "
        f"{BLUE}Ошибок:{NC} {RED}{failed}{NC} | "
        f"{BLUE}Пропущено:{NC} {GRAY}{skipped}{NC}"
    )
    print(f"{BLUE}========================================{NC}")

    print(f"{YELLOW}⏳ Ожидание инициализации (3 сек)...{NC}")
    time.sleep(3)
    print(f"{GREEN}✅ Готово!{NC}")
    print(f"{GREEN}   Проверка: python manage.py health{NC}")
    print(f"{GREEN}   Остановка: python manage.py stop{NC}")
    print(f"{GREEN}   Логи:      python manage.py logs{NC}")
    return 0 if failed == 0 else 1


def cmd_stop(args: argparse.Namespace) -> int:
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}🛑  Остановка микросервисов Volunteer+{NC}")
    print(f"{BLUE}========================================{NC}")

    targets = _resolve_services(args.services)
    target_names = {name for name, _ in targets}
    target_ports = {port for _, port in targets}

    stopped = 0

    # 1. Остановка по PID-файлам
    if PID_DIR.is_dir():
        for pid_file in sorted(PID_DIR.glob("*.pid")):
            service = pid_file.stem
            if service not in target_names:
                continue
            pid = _read_pid_file(pid_file)
            if pid is None:
                pid_file.unlink(missing_ok=True)
                continue

            print(f"  📍 {service} (PID: {pid})... ", end="", flush=True)
            if _kill_pid(pid):
                print(f"{GREEN}✓ остановлен{NC}")
                stopped += 1
            else:
                print(f"{YELLOW}уже остановлен{NC}")
            pid_file.unlink(missing_ok=True)

    # 2. Дополнительно по портам (если PID-файлов нет/устарели)
    print(f"{YELLOW}🔍 Проверка занятых портов...{NC}")
    for port in sorted(target_ports):
        pid = _pid_on_port(port)
        if pid is None:
            continue
        print(f"  📍 Порт {port} (PID: {pid})... ", end="", flush=True)
        if _kill_pid(pid):
            print(f"{GREEN}✓ остановлен{NC}")
            stopped += 1
        else:
            print(f"{YELLOW}не удалось остановить{NC}")

    # 3. Очистка PID-файлов
    print(f"{YELLOW}🧹 Очистка PID файлов...{NC}")
    if PID_DIR.is_dir():
        for pid_file in PID_DIR.glob("*.pid"):
            if pid_file.stem in target_names:
                pid_file.unlink(missing_ok=True)
    print(f"{GREEN}✅ PID файлы очищены{NC}")

    print(f"{BLUE}----------------------------------------{NC}")
    print(f"Остановлено сервисов: {GREEN}{stopped}{NC}")
    print(f"{BLUE}========================================{NC}")
    print(f"{GREEN}✅ Готово{NC}")
    return 0


def cmd_restart(args: argparse.Namespace) -> int:
    cmd_stop(args)
    time.sleep(1)
    return cmd_run(args)


# =============================================================================
# STATUS / HEALTH
# =============================================================================

def cmd_status(args: argparse.Namespace) -> int:
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}📊  Статус микросервисов Volunteer+{NC}")
    print(f"{BLUE}========================================{NC}")

    targets = _resolve_services(args.services)
    running = stopped = skipped = 0

    print()
    print(f"  {'СЕРВИС':<25} {'ПОРТ':<8} {'СТАТУС'}")
    print("  " + "-" * 44)

    for service, port in targets:
        service_dir = PROJECT_DIR / "app" / "services" / service
        pid_file = PID_DIR / f"{service}.pid"

        if not service_dir.is_dir() or not (service_dir / "main.py").is_file():
            print(f"  {service:<25} {port:<8} {GRAY}⊘ НЕ СУЩЕСТВУЕТ{NC}")
            skipped += 1
            continue

        status = f"{RED}✗ STOP{NC}"
        pid = _read_pid_file(pid_file)
        if pid is not None and _is_process_alive(pid):
            status = f"{GREEN}✓ RUN{NC}"
            running += 1
        elif pid is None and _is_port_open(port):
            status = f"{GREEN}✓ RUN{NC}"
            running += 1
        else:
            stopped += 1

        print(f"  {service:<25} {port:<8} {status}")

    print("  " + "-" * 44)
    print(
        f"  {GREEN}Запущено: {running}{NC} / "
        f"{RED}Остановлено: {stopped}{NC} / "
        f"{GRAY}Пропущено: {skipped}{NC}"
    )
    print(f"{BLUE}========================================{NC}")

    existing = running + stopped
    return 0 if (existing > 0 and running == existing) else 1


def _check_health_body(body: str) -> bool:
    try:
        data = json.loads(body)
        return data.get("status") == "healthy"
    except (json.JSONDecodeError, AttributeError):
        return '"status":"healthy"' in body.replace(" ", "")


def cmd_health(args: argparse.Namespace) -> int:
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}🏥  Health Check микросервисов{NC}")
    print(f"{BLUE}========================================{NC}")

    targets = _resolve_services(args.services)
    healthy = unhealthy = unreachable = skipped = 0

    print()
    print(f"  {'СЕРВИС':<25} {'ПОРТ':<8} {'СТАТУС':<15} {'ВРЕМЯ'}")
    print("  " + "-" * 56)

    for service, port in targets:
        service_dir = PROJECT_DIR / "app" / "services" / service
        url = f"http://127.0.0.1:{port}/health"

        if not service_dir.is_dir() or not (service_dir / "main.py").is_file():
            print(f"  {service:<25} {port:<8} {GRAY}⊘ НЕ СУЩЕСТВУЕТ{NC}")
            skipped += 1
            continue

        t0 = time.monotonic()
        try:
            with urlrequest.urlopen(url, timeout=2.0) as resp:
                code = resp.status
                body = resp.read().decode("utf-8", errors="replace")
        except URLError:
            code, body = None, None
        except Exception:
            code, body = None, None
        dt_ms = int((time.monotonic() - t0) * 1000)

        if code is None:
            print(f"  {service:<25} {port:<8} {RED}✗ UNREACHABLE{NC}")
            unreachable += 1
        elif code == 200 and body and _check_health_body(body):
            print(f"  {service:<25} {port:<8} {GREEN}✓ HEALTHY{NC}     {dt_ms}мс")
            healthy += 1
        else:
            print(f"  {service:<25} {port:<8} {YELLOW}⚠ HTTP {code}{NC}    {dt_ms}мс")
            unhealthy += 1

    print("  " + "-" * 56)
    print(
        f"  {GREEN}Здоровы: {healthy}{NC} | "
        f"{YELLOW}Проблемы: {unhealthy}{NC} | "
        f"{RED}Недоступны: {unreachable}{NC} | "
        f"{GRAY}Пропущено: {skipped}{NC}"
    )
    print(f"{BLUE}========================================{NC}")

    if unreachable > 0:
        print(f"{RED}⚠  Некоторые сервисы недоступны!{NC}")
        print("   Запустите: python manage.py run")
        return 1
    if unhealthy > 0:
        print(f"{YELLOW}⚠  Некоторые сервисы вернули ошибки!{NC}")
        return 1
    print(f"{GREEN}✅ Все существующие сервисы работают корректно!{NC}")
    return 0


# =============================================================================
# LOGS
# =============================================================================

def cmd_logs(args: argparse.Namespace) -> int:
    if not LOG_DIR.is_dir():
        print(f"❌ Директория логов не найдена: {LOG_DIR}")
        return 1

    targets = _resolve_services(args.services)
    target_names = [name for name, _ in targets]

    log_files = [
        LOG_DIR / f"{name}.log" for name in target_names
        if (LOG_DIR / f"{name}.log").is_file()
    ]

    if not log_files:
        print(f"⚠️  Лог-файлов не найдено в {LOG_DIR}")
        print("   Сначала запустите сервисы: python manage.py run")
        return 0

    print("📋 Логи микросервисов (Ctrl+C для выхода)")
    print(f"   Директория: {LOG_DIR}")
    print()

    handles: dict[Path, "os.PathLike | None"] = {}
    for lf in log_files:
        for line in _tail_lines(lf, args.lines):
            print(f"[{lf.name}] {line.rstrip()}", flush=True)
        try:
            f = lf.open("r", encoding="utf-8", errors="replace")
            f.seek(0, 2)  # конец файла
            handles[lf] = f  # type: ignore[assignment]
        except OSError as e:
            print(f"⚠️  Не удалось открыть {lf}: {e}")

    if args.no_follow:
        for f in handles.values():
            try:
                f.close()  # type: ignore[union-attr]
            except OSError:
                pass
        return 0

    try:
        while True:
            for lf, f in list(handles.items()):
                while True:
                    line = f.readline()  # type: ignore[union-attr]
                    if not line:
                        break
                    print(f"[{lf.name}] {line.rstrip()}", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
    finally:
        for f in handles.values():
            try:
                f.close()  # type: ignore[union-attr]
            except OSError:
                pass
    return 0


# =============================================================================
# SEED
# =============================================================================

async def _seed_async(project_dir: Path) -> None:
    """Наполнить БД тестовыми данными.

    ВАЖНО: эта функция выполняется только в процессе, запущенном через
    venv-python (см. _ensure_venv_or_reexec). Все тяжёлые импорты — локальные,
    чтобы manage.py работал на голом системном Python для команд
    run/stop/status/health/logs.
    """
    # --- тяжёлые импорты (нужны только здесь) ---
    from sqlalchemy.ext.asyncio import (
        create_async_engine, AsyncSession, async_sessionmaker,
    )

    from app.services.user_service.db.models import (
        Base as UserBase, User, UserSettings, UserLocation, UserRoleEnum,
    )
    from app.services.organization_service.db.models import (
        Base as OrgBase, Organization, Category,
    )
    from app.services.event_service.db.models import (
        Base as EventBase, Event, Participation, ParticipationStatus,
    )
    from app.services.subscription_service.db.models import (
        Base as SubBase, Subscription, SubscriptionLog,
    )
    from app.services.chat_service.db.models import (
        Base as ChatBase, Chat, ChatMember, Message, ChatTypeEnum, MessageTypeEnum,
    )
    from app.services.analytics_service.db.models import (
        Base as AnalyticsBase, VolunteerStats, MonthlyStats, PreferredRole,
    )
    from app.services.user_service.core.security import hash_password

    volunteer_url = f"sqlite+aiosqlite:///{project_dir}/volunteer_plus.db"
    user_url = f"sqlite+aiosqlite:///{project_dir}/users.db"

    volunteer_engine = create_async_engine(volunteer_url, echo=False, future=True)
    user_engine = create_async_engine(user_url, echo=False, future=True)

    user_session = async_sessionmaker(user_engine, class_=AsyncSession, expire_on_commit=False)
    volunteer_session = async_sessionmaker(volunteer_engine, class_=AsyncSession, expire_on_commit=False)

    def now_utc() -> datetime:
        return datetime.now(timezone.utc)

    try:
        # 1. Создать все таблицы
        async with user_engine.begin() as conn:
            await conn.run_sync(UserBase.metadata.create_all)

        async with volunteer_engine.begin() as conn:
            await conn.run_sync(OrgBase.metadata.create_all)
            await conn.run_sync(EventBase.metadata.create_all)
            await conn.run_sync(SubBase.metadata.create_all)
            await conn.run_sync(ChatBase.metadata.create_all)
            await conn.run_sync(AnalyticsBase.metadata.create_all)

        # 2. Очистить (порядок важен для FK)
        async with user_engine.begin() as conn:
            for table in (
                UserSettings.__table__,
                UserLocation.__table__,
                User.__table__,
            ):
                await conn.execute(table.delete())

        async with volunteer_engine.begin() as conn:
            for table in (
                # Chat → Message/ChatMember
                Message.__table__,
                ChatMember.__table__,
                Chat.__table__,
                # Subscription
                SubscriptionLog.__table__,
                Subscription.__table__,
                # Event → Participation
                Participation.__table__,
                Event.__table__,
                # Org → Category
                Organization.__table__,
                Category.__table__,
                # Analytics
                VolunteerStats.__table__,
                MonthlyStats.__table__,
                PreferredRole.__table__,
            ):
                await conn.execute(table.delete())

        # 3. Пользователи (users.db)
        async with user_session() as s:
            for uid, email, pwd, full_name, phone, role in [
                (1, "user1@example.com", "password123", "Иван Петров", "+79991111111", UserRoleEnum.VOLUNTEER),
                (2, "user2@example.com", "password123", "Мария Сидорова", "+79992222222", UserRoleEnum.VOLUNTEER),
                (3, "admin@example.com", "admin123", "Алексей Администратор", "+79993333333", UserRoleEnum.ADMIN),
            ]:
                s.add(User(
                    id=uid, email=email, password_hash=hash_password(pwd),
                    full_name=full_name, phone=phone, role=role,
                    is_active=True, is_verified=True,
                    created_at=now_utc(), last_login=now_utc(),
                ))
                s.add(UserSettings(
                    user_id=uid, search_radius_km=10, language="ru", theme="light",
                ))
                s.add(UserLocation(
                    user_id=uid, latitude=55.7558, longitude=37.6173,
                    accuracy=10.0, updated_at=now_utc(),
                ))
            await s.commit()

        # 4. Остальные данные (volunteer_plus.db)
        async with volunteer_session() as s:
            # --- Categories ---
            for cid, name in [
                (1, "Экология"),
                (2, "Помощь детям"),
                (3, "Помощь пожилым"),
                (4, "Защита животных"),
                (5, "Образование"),
            ]:
                s.add(Category(id=cid, name=name))

            # --- Organizations ---
            for oid, name, desc, verified, rating, cat in [
                (1, "Эко-Движение", "Защита окружающей среды", True, 4.9, 1),
                (2, "Дети-Герои", "Помощь детям в трудной ситуации", True, 4.7, 2),
                (3, "Помощь пожилым", "Забота о старшем поколении", True, 4.5, 3),
                (4, "Защита животных", "Приют для бездомных животных", False, 4.2, 4),
                (5, "Образование для всех", "Бесплатные курсы", True, 4.8, 5),
            ]:
                s.add(Organization(
                    id=oid, name=name, description=desc,
                    is_verified=verified, rating=rating, category_id=cat,
                ))

            # --- Events ---
            # (id, org_id, title, description, days_from_now, duration_h, location, max, qr_secret)
            now = now_utc()
            events_spec = [
                (1, 1, "Уборка парка Горького", "Ежемесячная уборка", 3, 4, "Парк Горького", 50, "qr_secret_1"),
                (2, 1, "Посадка деревьев", "Озеленение", 10, 5, "Сквер Вернисаж", 30, "qr_secret_2"),
                (3, 2, "Праздник для детей", "Концерт и игры", 5, 6, "Детский дом №5", 20, "qr_secret_3"),
                (4, 3, "Помощь в доме престарелых", "Концерт и общение", 7, 4, "Дом престарелых", 15, "qr_secret_4"),
                (5, 4, "Выгул собак", "Прогулка с собаками из приюта", 2, 3, "Приют 'Лучший друг'", 10, "qr_secret_5"),
                (6, 1, "Субботник (прошедшее)", "Уборка в прошлом", -20, 4, "Парк Горького", 50, "qr_secret_6"),
                (7, 5, "Курс 'Волонтёрство 101'", "Обучение", 15, 48, "Online", 100, "qr_secret_7"),
            ]
            for eid, org_id, title, desc, days, dur_h, loc, mx, secret in events_spec:
                start = now + timedelta(days=days)
                s.add(Event(
                    id=eid, org_id=org_id, title=title, description=desc,
                    start_date=start, end_date=start + timedelta(hours=dur_h),
                    location=loc, max_participants=mx, qr_secret=secret,
                ))

            # --- Participations ---
            s.add(Participation(event_id=1, user_id=1, status=ParticipationStatus.CHECKED_IN,
                                registered_at=now - timedelta(days=1),
                                checked_in_at=now - timedelta(days=1)))
            s.add(Participation(event_id=2, user_id=1, status=ParticipationStatus.REGISTERED,
                                registered_at=now - timedelta(days=2)))
            s.add(Participation(event_id=6, user_id=1, status=ParticipationStatus.CHECKED_IN,
                                registered_at=now - timedelta(days=25),
                                checked_in_at=now - timedelta(days=20)))
            s.add(Participation(event_id=3, user_id=2, status=ParticipationStatus.CHECKED_IN,
                                registered_at=now - timedelta(days=3),
                                checked_in_at=now - timedelta(days=2)))

            # --- Subscriptions ---
            for sid, uid, oid, role in [
                (1, 1, 1, "volunteer"),
                (2, 1, 2, "volunteer"),
                (3, 2, 1, "volunteer"),
                (4, 2, 4, "volunteer"),
            ]:
                s.add(Subscription(id=sid, user_id=uid, org_id=oid, role=role, active=True))
                s.add(SubscriptionLog(user_id=uid, org_id=oid,
                                      action="SUBSCRIBE", subscription_id=sid))

            # --- Chats + messages ---
            s.add(Chat(id=1, chat_type=ChatTypeEnum.ORGANIZER,
                       organization_id=1, is_active=True, created_at=now))
            s.add(ChatMember(chat_id=1, user_id=1, role="member", joined_at=now))
            s.add(ChatMember(chat_id=1, user_id=3, role="admin", joined_at=now))

            s.add(Chat(id=2, chat_type=ChatTypeEnum.EVENT,
                       title="Чат: Уборка парка", event_id=1,
                       organization_id=1, is_active=True, created_at=now))
            s.add(ChatMember(chat_id=2, user_id=1, role="member", joined_at=now))
            s.add(ChatMember(chat_id=2, user_id=2, role="member", joined_at=now))
            s.add(ChatMember(chat_id=2, user_id=3, role="admin", joined_at=now))

            s.add(Message(id=1, chat_id=1, sender_id=3,
                          content="Здравствуйте! Готовы помочь?",
                          message_type=MessageTypeEnum.TEXT, is_read=True,
                          created_at=now - timedelta(hours=2)))
            s.add(Message(id=2, chat_id=1, sender_id=1,
                          content="Да, интересует мероприятие по посадке деревьев",
                          message_type=MessageTypeEnum.TEXT, is_read=True,
                          created_at=now - timedelta(hours=1)))
            s.add(Message(id=3, chat_id=2, sender_id=3,
                          content="Встречаемся в 10:00 у главного входа!",
                          message_type=MessageTypeEnum.TEXT, is_read=False,
                          created_at=now - timedelta(minutes=30)))

            # --- Analytics ---
            s.add(VolunteerStats(user_id=1, organization_id=1, role="volunteer",
                                 hours_worked=12.0, events_completed=3,
                                 last_activity=now))
            s.add(VolunteerStats(user_id=1, organization_id=2, role="volunteer",
                                 hours_worked=6.0, events_completed=1,
                                 last_activity=now))
            s.add(VolunteerStats(user_id=2, organization_id=1, role="volunteer",
                                 hours_worked=4.0, events_completed=1,
                                 last_activity=now))

            base = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            for i in range(6):
                month_date = base - timedelta(days=30 * i)
                hours = 8.0 * (6 - i)
                s.add(MonthlyStats(
                    user_id=1, year=month_date.year, month=month_date.month,
                    hours_worked=hours, events_completed=int(hours / 4),
                ))
            s.add(MonthlyStats(user_id=2, year=base.year, month=base.month,
                               hours_worked=4.0, events_completed=1))

            s.add(PreferredRole(user_id=1, role="volunteer", score=18.0, events_count=4))
            s.add(PreferredRole(user_id=1, role="coordinator", score=6.0, events_count=1))
            s.add(PreferredRole(user_id=2, role="volunteer", score=4.0, events_count=1))

            await s.commit()

    finally:
        await user_engine.dispose()
        await volunteer_engine.dispose()


def cmd_seed(args: argparse.Namespace) -> int:
    # Для seed нужны SQLAlchemy/bcrypt/модели — гарантируем venv
    if not _ensure_venv_or_reexec():
        return 1

    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}🌱  Seed Database — Volunteer+{NC}")
    print(f"{BLUE}========================================{NC}")

    # 1. Проверка запущенных сервисов
    running = [name for name, port in SERVICES if _is_port_open(port)]
    if running:
        print(f"{YELLOW}🔍 Обнаружены запущенные сервисы:{NC}")
        for name in running:
            print(f"  ⚠️  {name}")
        print()
        print(f"{RED}❌ Seed может повредить данные, если сервисы пишут в БД.{NC}")
        stop = args.yes or _ask_yes_no("🛑 Остановить сервисы и продолжить?")
        if not stop:
            print(f"{RED}❌ Seed отменён{NC}")
            return 1
        print(f"{YELLOW}Остановка сервисов...{NC}")
        subprocess.run([sys.executable, str(SELF), "stop"], cwd=str(PROJECT_DIR))

    # 2. Удаление старых БД
    wipe = args.yes or _ask_yes_no("🗑️  Удалить старые базы данных?")
    if wipe:
        print(f"{YELLOW}Удаление старых БД...{NC}")
        for name in (
            "volunteer_plus.db",
            "users.db",
            "test_volunteer_plus.db",
            "test_org.db",
        ):
            p = PROJECT_DIR / name
            if p.exists():
                try:
                    p.unlink()
                    print(f"   ✓ удалён {name}")
                except OSError as e:
                    print(f"   {RED}не удалось удалить {name}: {e}{NC}")
        print(f"{GREEN}✅ Старые БД удалены (или отсутствовали){NC}")

    # 3. Запуск seed
    print(f"{YELLOW}🌱 Наполнение БД тестовыми данными...{NC}")
    try:
        asyncio.run(_seed_async(PROJECT_DIR))
    except Exception as e:
        print(f"{RED}❌ Ошибка seed: {e}{NC}")
        import traceback
        traceback.print_exc()
        return 1

    print()
    print(f"{BLUE}========================================{NC}")
    print(f"{GREEN}✅ Seed завершён успешно!{NC}")
    print(f"{BLUE}========================================{NC}")
    print()
    print(f"{YELLOW}📊 Тестовые учётные данные:{NC}")
    print("   user1@example.com / password123")
    print("   user2@example.com / password123")
    print("   admin@example.com / admin123")
    print()
    print(f"{YELLOW}💾 Файлы БД:{NC}")
    print(f"   - {PROJECT_DIR / 'users.db'}")
    print(f"   - {PROJECT_DIR / 'volunteer_plus.db'}")
    print()
    print(f"{GREEN}🚀 Запустите: python manage.py run{NC}")
    return 0


# =============================================================================
# CLI
# =============================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Volunteer+ — управление микросервисами.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Примеры:\n"
            "  python manage.py run\n"
            "  python manage.py run user_service chat_service\n"
            "  python manage.py stop feed\n"
            "  python manage.py health\n"
            "  python manage.py logs -n 50 user\n"
            "  python manage.py seed --yes\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    p_run = sub.add_parser("run", help="Запустить сервисы")
    p_run.add_argument("services", nargs="*", help="Имена сервисов (по умолчанию все)")
    p_run.set_defaults(func=cmd_run)

    p_stop = sub.add_parser("stop", help="Остановить сервисы")
    p_stop.add_argument("services", nargs="*")
    p_stop.set_defaults(func=cmd_stop)

    p_restart = sub.add_parser("restart", help="Перезапустить сервисы")
    p_restart.add_argument("services", nargs="*")
    p_restart.set_defaults(func=cmd_restart)

    p_status = sub.add_parser("status", help="Быстрый статус (PID/порт)")
    p_status.add_argument("services", nargs="*")
    p_status.set_defaults(func=cmd_status)

    p_health = sub.add_parser("health", help="Health-check через /health")
    p_health.add_argument("services", nargs="*")
    p_health.set_defaults(func=cmd_health)

    p_logs = sub.add_parser("logs", help="Просмотр логов (tail -f)")
    p_logs.add_argument("services", nargs="*")
    p_logs.add_argument("-n", "--lines", type=int, default=10,
                        help="Сколько последних строк показать при старте (по умолчанию 10)")
    p_logs.add_argument("--no-follow", action="store_true",
                        help="Показать текущий хвост и выйти")
    p_logs.set_defaults(func=cmd_logs)

    p_seed = sub.add_parser("seed", help="Наполнить БД тестовыми данными")
    p_seed.add_argument("-y", "--yes", action="store_true",
                        help="Не задавать вопросов (согласие по умолчанию)")
    p_seed.set_defaults(func=cmd_seed)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 0

    try:
        return int(args.func(args))
    except KeyboardInterrupt:
        print()
        return 130
    except Exception as e:
        print(f"{RED}❌ Непредвиденная ошибка: {e}{NC}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
