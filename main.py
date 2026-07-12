import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import flet as ft
import requests

BMKG_API_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
DEFAULT_LOCATION_QUERY = "Banjarmasin"
ADM4_PATTERN = re.compile(r"^\d{2}\.\d{2}\.\d{2}\.\d{4}$")

LOCATION_ALIASES = {
    "banjarmasin": "63.71.05.1001",
    "banjarmasin tengah": "63.71.05.1001",
    "kertak baru ilir": "63.71.05.1001",
    "mantuil": "63.71.01.1001",
    "kelayan timur": "63.71.01.1008",
    "pemurus luar": "63.71.02.1009",
    "belitung utara": "63.71.03.1001",
    "belitung selatan": "63.71.03.1002",
    "pelambuan": "63.71.03.1003",
    "telaga biru": "63.71.03.1004",
    "kemayoran": "31.71.03.1001",
    "jakarta": "31.71.03.1001",
    "jakarta pusat": "31.71.03.1001",
    "banda aceh": "11.71.01.2001",
    "medan": "12.71.01.1002",
    "padang": "13.71.03.1005",
    "pekanbaru": "14.71.02.1001",
    "jambi": "15.71.04.1003",
    "palembang": "16.71.11.1002",
    "bengkulu": "17.71.03.1001",
    "bandar lampung": "18.71.06.1002",
    "lampung": "18.71.06.1002",
    "batam": "21.71.10.1003",
    "bogor": "32.71.03.1003",
    "bandung": "32.73.19.1002",
    "bekasi": "32.75.04.1002",
    "depok": "32.76.01.1006",
    "semarang": "33.74.01.1013",
    "surakarta": "33.72.05.1006",
    "solo": "33.72.05.1006",
    "yogyakarta": "34.71.10.1001",
    "jogja": "34.71.10.1001",
    "surabaya": "35.78.07.1002",
    "malang": "35.73.02.1001",
    "tangerang": "36.71.01.1001",
    "denpasar": "51.71.03.1005",
    "mataram": "52.71.02.1002",
    "kupang": "53.71.05.1004",
    "pontianak": "61.71.05.1003",
    "balikpapan": "64.71.06.1003",
    "samarinda": "64.72.09.1004",
    "manado": "71.71.04.1005",
    "palu": "72.71.01.1006",
    "makassar": "73.71.04.1008",
    "kendari": "74.71.01.1006",
    "ambon": "81.71.02.1017",
    "jayapura": "91.71.01.1001",
}

NAMA_HARI = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu",
}

ARAH_ANGIN = {
    "N": "Utara",
    "NNE": "Utara-Timur Laut",
    "NE": "Timur Laut",
    "ENE": "Timur-Timur Laut",
    "E": "Timur",
    "ESE": "Timur-Tenggara",
    "SE": "Tenggara",
    "SSE": "Selatan-Tenggara",
    "S": "Selatan",
    "SSW": "Selatan-Barat Daya",
    "SW": "Barat Daya",
    "WSW": "Barat-Barat Daya",
    "W": "Barat",
    "WNW": "Barat-Barat Laut",
    "NW": "Barat Laut",
    "NNW": "Utara-Barat Laut",
    "VARIABLE": "Berubah-ubah",
    "CALM": "Tenang",
}


class WeatherAPIError(Exception):
    pass

def normalize_query(value: str) -> str:
    return " ".join(value.strip().lower().split())

def resolve_adm4(query: str) -> str:
    cleaned = query.strip()

    if ADM4_PATTERN.fullmatch(cleaned):
        return cleaned

    alias = LOCATION_ALIASES.get(normalize_query(cleaned))
    if alias:
        return alias

    raise WeatherAPIError(
    )

def fetch_bmkg_weather(adm4_code: str) -> dict[str, Any]:
    try:
        response = requests.get(
            BMKG_API_URL,
            params={"adm4": adm4_code},
            headers={"User-Agent": "WeatherAppFlet/1.0"},
            timeout=20,
        )

        if response.status_code == 429:
            raise WeatherAPIError(
            )

        if response.status_code in {400, 404}:
            raise WeatherAPIError(
                f'Kode wilayah "{adm4_code}" tidak ditemukan oleh BMKG.'
            )

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as error:
            raise WeatherAPIError(
                "Respons BMKG bukan data JSON yang valid. Silakan coba lagi."
            ) from error

    except WeatherAPIError:
        raise
    except requests.Timeout as error:
        raise WeatherAPIError(
            "Permintaan ke BMKG terlalu lama. Periksa internet lalu coba lagi."
        ) from error
    except requests.ConnectionError as error:
        raise WeatherAPIError(
            "Tidak dapat terhubung ke BMKG. Periksa koneksi internet Anda."
        ) from error
    except requests.RequestException as error:
        raise WeatherAPIError(
            "Data cuaca BMKG gagal diambil. Silakan coba kembali."
        ) from error

    if not isinstance(data, dict):
        raise WeatherAPIError("Format data dari BMKG tidak sesuai.")

    location = data.get("lokasi")
    forecast_data = data.get("data")

    if not isinstance(location, dict):
        raise WeatherAPIError("Informasi lokasi tidak ditemukan pada data BMKG.")

    if not isinstance(forecast_data, list) or not forecast_data:
        raise WeatherAPIError("Prakiraan cuaca tidak ditemukan pada data BMKG.")

    return data

def extract_weather_days(api_data: dict[str, Any]) -> list[list[dict[str, Any]]]:
    data_list = api_data.get("data")
    if not isinstance(data_list, list) or not data_list:
        raise WeatherAPIError("Struktur prakiraan BMKG tidak lengkap.")

    weather_groups = data_list[0].get("cuaca")
    if not isinstance(weather_groups, list):
        raise WeatherAPIError("Daftar prakiraan cuaca BMKG tidak ditemukan.")

    days: list[list[dict[str, Any]]] = []
    for raw_day in weather_groups:
        if not isinstance(raw_day, list):
            continue

        valid_entries = [item for item in raw_day if isinstance(item, dict)]
        if valid_entries:
            days.append(valid_entries)

        if len(days) == 3:
            break

    if not days:
        raise WeatherAPIError("Data prakiraan cuaca BMKG masih kosong.")

    return days

def parse_bmkg_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)

    return parsed

def get_location_now(location: dict[str, Any]) -> datetime:
    timezone_name = location.get("timezone")
    if isinstance(timezone_name, str) and timezone_name:
        try:
            return datetime.now(ZoneInfo(timezone_name)).replace(tzinfo=None)
        except (ZoneInfoNotFoundError, ValueError):
            pass

    return datetime.now()

def flatten_days(days: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [entry for day in days for entry in day]

def get_nearest_forecast(
    days: list[list[dict[str, Any]]],
    location: dict[str, Any],
) -> dict[str, Any]:
    entries = flatten_days(days)
    if not entries:
        raise WeatherAPIError("Tidak ada jadwal prakiraan yang dapat ditampilkan.")

    now = get_location_now(location)
    dated_entries: list[tuple[dict[str, Any], datetime]] = []

    for entry in entries:
        parsed = parse_bmkg_datetime(entry.get("local_datetime"))
        if parsed is not None:
            dated_entries.append((entry, parsed))

    if not dated_entries:
        return entries[0]

    future_entries = [item for item in dated_entries if item[1] >= now]
    if future_entries:
        return min(future_entries, key=lambda item: item[1] - now)[0]

    return min(dated_entries, key=lambda item: abs(item[1] - now))[0]

def weather_emoji(description: Any, local_datetime: Any = None) -> str:
    text = str(description or "").lower()
    parsed_time = parse_bmkg_datetime(local_datetime)
    hour = parsed_time.hour if parsed_time else 12
    is_day = 6 <= hour < 18

    if "petir" in text:
        return "⛈️"
    if "hujan lebat" in text:
        return "🌧️"
    if "hujan" in text or "gerimis" in text:
        return "🌦️"
    if "kabut" in text or "asap" in text or "udara kabur" in text:
        return "🌫️"
    if "berawan tebal" in text or "mendung" in text:
        return "☁️"
    if "cerah berawan" in text:
        return "🌤️" if is_day else "☁️"
    if "berawan" in text:
        return "⛅" if is_day else "☁️"
    if "cerah" in text:
        return "☀️" if is_day else "🌙"
    return "🌡️"
def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def format_number(value: Any, digits: int = 0) -> str:
    number = safe_number(value)
    if digits == 0:
        return str(round(number))
    return f"{number:.{digits}f}".rstrip("0").rstrip(".")

def format_forecast_datetime(value: Any) -> str:
    parsed = parse_bmkg_datetime(value)
    if parsed is None:
        return "Waktu tidak tersedia"

    day_name = NAMA_HARI[parsed.weekday()]
    return f"{day_name}, {parsed.strftime('%d/%m/%Y • %H.%M')}"

def get_wind_direction(code: Any) -> str:
    normalized = str(code or "-").upper()
    return ARAH_ANGIN.get(normalized, normalized)

def main(page: ft.Page) -> None:
    page.title = "Cuaca - Flet"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#08111F"
    page.padding = 0
    page.scroll = ft.ScrollMode.AUTO

    title = ft.Text("Cuaca", size=30, weight=ft.FontWeight.BOLD)
    subtitle = ft.Text(
        "Prakiraan cuaca kota/kelurahan/desa di Indonesia",
        size=14,
        color="#B9C7DC",
    )

    location_input = ft.TextField(
        value=DEFAULT_LOCATION_QUERY,
        hint_text="Contoh: Banjarmasin atau 63.71.05.1001",
        prefix_icon=ft.Icons.LOCATION_CITY,
        border_radius=16,
        border_color="#334155",
        focused_border_color="#60A5FA",
        bgcolor="#101C2E",
        color="#F8FAFC",
        expand=True,
    )

    loading = ft.ProgressRing(
        width=30,
        height=30,
        stroke_width=3,
        color="#60A5FA",
        visible=False,
    )
    status_text = ft.Text("", color="#FCA5A5", size=14)
    weather_content = ft.Column(spacing=18)

    search_button = ft.Button(
        content="Tampilkan Cuaca",
        icon=ft.Icons.SEARCH,
        bgcolor="#2563EB",
        color="#FFFFFF",
        height=52,
    )

    def set_loading(is_loading: bool) -> None:
        loading.visible = is_loading
        search_button.disabled = is_loading
        location_input.disabled = is_loading
        page.update()

    def info_box(icon: ft.IconData, label: str, value: str) -> ft.Container:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Icon(icon, color="#93C5FD", size=25),
                        width=46,
                        height=46,
                        alignment=ft.Alignment.CENTER,
                        bgcolor="#172A46",
                        border_radius=14,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(label, size=12, color="#94A3B8"),
                            ft.Text(
                                value,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                no_wrap=False,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                ],
                spacing=12,
            ),
            padding=14,
            bgcolor="#101C2E",
            border_radius=16,
            border=ft.Border.all(1, "#22324A"),
            col={"xs": 12, "sm": 6, "md": 3},
        )

    def display_weather(api_data: dict[str, Any], adm4_code: str) -> None:
        location = api_data["lokasi"]
        days = extract_weather_days(api_data)
        nearest = get_nearest_forecast(days, location)

        description = str(nearest.get("weather_desc") or "Tidak diketahui")
        emoji = weather_emoji(description, nearest.get("local_datetime"))

        village = str(location.get("desa") or "Lokasi tidak diketahui")
        district = str(location.get("kecamatan") or "-")
        city = str(location.get("kotkab") or "-")
        province = str(location.get("provinsi") or "-")
        timezone_name = str(location.get("timezone") or "-")

        current_card = ft.Container(
            content=ft.ResponsiveRow(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.LOCATION_ON,
                                        color="#BFDBFE",
                                        size=20,
                                    ),
                                    ft.Text(
                                        village,
                                        size=19,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=6,
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                            ft.Text(
                                f"{district}, {city}",
                                size=13,
                                color="#DBEAFE",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                province,
                                size=12,
                                color="#BFDBFE",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(emoji, size=78),
                            ft.Text(description, size=18, color="#DBEAFE"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        col={"xs": 12, "md": 5},
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                f'{format_number(nearest.get("t"))}°C',
                                size=66,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Prakiraan waktu terdekat",
                                size=15,
                                color="#DBEAFE",
                            ),
                            ft.Text(
                                format_forecast_datetime(
                                    nearest.get("local_datetime")
                                ),
                                size=12,
                                color="#BFDBFE",
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                f"Kode wilayah: {adm4_code}",
                                size=11,
                                color="#93C5FD",
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                        col={"xs": 12, "md": 7},
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=24,
            border_radius=24,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,
                end=ft.Alignment.BOTTOM_RIGHT,
                colors=["#1D4ED8", "#0F766E"],
            ),
        )

        details = ft.ResponsiveRow(
            controls=[
                info_box(
                    ft.Icons.WATER_DROP,
                    "Kelembapan",
                    f'{format_number(nearest.get("hu"))}%',
                ),
                info_box(
                    ft.Icons.AIR,
                    "Kecepatan angin",
                    f'{format_number(nearest.get("ws"), 1)} km/jam',
                ),
                info_box(
                    ft.Icons.EXPLORE,
                    "Arah angin dari",
                    get_wind_direction(nearest.get("wd")),
                ),
                info_box(
                    ft.Icons.VISIBILITY,
                    "Jarak pandang",
                    str(nearest.get("vs_text") or "-"),
                ),
                info_box(
                    ft.Icons.CLOUD,
                    "Tutupan awan",
                    f'{format_number(nearest.get("tcc"))}%',
                ),
                info_box(
                    ft.Icons.PUBLIC,
                    "Zona waktu",
                    timezone_name,
                ),
            ],
            spacing=12,
            run_spacing=12,
        )

        analysis_date = nearest.get("analysis_date")
        analysis_text = (
            f"Waktu produksi data BMKG: {str(analysis_date).replace('T', ' ')}"
            if analysis_date
            else ""
        )

        weather_content.controls = [
            current_card,
            details,
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Sumber data: BMKG (Badan Meteorologi, Klimatologi, dan Geofisika)",
                            size=12,
                            color="#94A3B8",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            analysis_text,
                            size=11,
                            color="#64748B",
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=3,
                ),
                alignment=ft.Alignment.CENTER,
                padding=10,
            ),
        ]

    def load_weather(event: ft.Event | None = None) -> None:
        query = location_input.value.strip()
        status_text.value = ""

        if not query:
            status_text.value = "Masukkan nama alias atau kode wilayah ADM4."
            page.update()
            return

        set_loading(True)
        try:
            adm4_code = resolve_adm4(query)
            api_data = fetch_bmkg_weather(adm4_code)
            display_weather(api_data, adm4_code)
        except WeatherAPIError as error:
            weather_content.controls.clear()
            status_text.value = str(error)
        except (KeyError, TypeError, ValueError) as error:
            weather_content.controls.clear()
            status_text.value = (
                "Data BMKG tidak dapat diproses. Silakan coba lagi beberapa saat."
            )
            print(f"Kesalahan pemrosesan data BMKG: {error}")
        finally:
            set_loading(False)
            page.update()

    search_button.on_click = load_weather
    location_input.on_submit = load_weather

    header = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.CLOUD,
                                color="#FFFFFF",
                                size=30,
                            ),
                            width=52,
                            height=52,
                            alignment=ft.Alignment.CENTER,
                            bgcolor="#2563EB",
                            border_radius=16,
                        ),
                        ft.Column(controls=[title, subtitle], spacing=2),
                    ],
                    spacing=14,
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            content=location_input,
                            col={"xs": 12, "md": 9},
                        ),
                        ft.Container(
                            content=search_button,
                            col={"xs": 12, "md": 3},
                        ),
                    ],
                    spacing=10,
                    run_spacing=10,
                ),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.INFO_OUTLINE, size=17, color="#93C5FD"),
                        ft.Text(
                            "Silahkan Ketik Nama Kota Anda, Jika Tidak Tersedia, Silahkan Masukkan Kode AMD4 Kota Anda"
                            ,
                            size=11,
                            color="#94A3B8",
                            expand=True,
                        ),
                    ],
                    spacing=7,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Row(
                    controls=[loading, status_text],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=18,
        ),
        padding=ft.Padding.only(left=24, top=24, right=24, bottom=18),
    )

    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    header,
                    ft.Container(
                        content=weather_content,
                        padding=ft.Padding.only(left=24, right=24, bottom=30),
                    ),
                ],
                spacing=0,
            )
        )
    )

    load_weather()

if __name__ == "__main__":
    ft.run(main)
