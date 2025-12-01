"""
PDF Report Generator

Generates PDF weather reports with charts and formatted data.

LIMITATIONS OF CURRENT IMPLEMENTATION:
- Uses basic PDF structure without proper PDF library
- Text only, no images or complex formatting
- Fixed font (Courier)
- Simple text-based charts instead of graphical charts
- Limited to approximately one page of content

FOR PRODUCTION USE:
- Install reportlab: pip install reportlab
- Replace _create_simple_pdf() with proper reportlab implementation
- Add matplotlib for graphical charts: pip install matplotlib
- Consider using weasyprint for HTML-to-PDF conversion
"""

import io
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


class PDFReportGenerator:
    """
    Generates PDF weather reports.
    
    Current implementation creates basic valid PDFs with:
    - Weather data tables as plain text
    - ASCII-based temperature charts
    - Basic branding and metadata
    
    For production, upgrade to reportlab for:
    - Rich formatting and fonts
    - Graphical charts with matplotlib
    - Multiple pages
    - Images and logos
    """
    
    def __init__(self):
        """Initialize the PDF generator."""
        self._branding = {
            "title": "IntelliWeather Report",
            "company": "IntelliWeather",
            "tagline": "Your Premium Weather Companion"
        }
    
    def generate(
        self,
        location: str,
        weather_data: Dict[str, Any],
        report_type: str = "daily"
    ) -> bytes:
        """
        Generate a PDF report.
        
        Args:
            location: Location name
            weather_data: Weather data dict
            report_type: "hourly" or "daily"
            
        Returns:
            PDF content as bytes
        """
        # Generate a simple text-based PDF structure
        # In production, use reportlab for proper PDF generation
        
        content = self._build_content(location, weather_data, report_type)
        
        # Create a minimal PDF structure
        pdf_bytes = self._create_simple_pdf(content)
        
        return pdf_bytes
    
    def _build_content(
        self,
        location: str,
        weather_data: Dict[str, Any],
        report_type: str
    ) -> str:
        """Build the report content."""
        now = datetime.now(timezone.utc)
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"  {self._branding['title']}")
        lines.append(f"  {self._branding['tagline']}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Location: {location}")
        lines.append(f"Report Type: {report_type.title()} Forecast")
        lines.append(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")
        
        if report_type == "hourly":
            lines.extend(self._format_hourly_data(weather_data))
        else:
            lines.extend(self._format_daily_data(weather_data))
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("")
        lines.append("Data Source: Open-Meteo API")
        lines.append(f"Powered by {self._branding['company']}")
        lines.append("")
        
        return "\n".join(lines)
    
    def _format_hourly_data(self, data: Dict[str, Any]) -> List[str]:
        """Format hourly forecast data."""
        lines = []
        lines.append("HOURLY FORECAST")
        lines.append("")
        lines.append(f"{'Time':<20} {'Temp':<10} {'Humidity':<10} {'Precip %':<10}")
        lines.append("-" * 50)
        
        hourly = data.get("hourly", [])
        for hour in hourly[:24]:
            time_str = hour.get("time", "")[:16]
            temp = f"{hour.get('temperature', '--')}°"
            humidity = f"{hour.get('humidity', '--')}%"
            precip = f"{hour.get('precipitation_probability', '--')}%"
            lines.append(f"{time_str:<20} {temp:<10} {humidity:<10} {precip:<10}")
        
        return lines
    
    def _format_daily_data(self, data: Dict[str, Any]) -> List[str]:
        """Format daily forecast data."""
        lines = []
        lines.append("7-DAY FORECAST")
        lines.append("")
        lines.append(f"{'Date':<15} {'Max':<8} {'Min':<8} {'Precip':<10} {'Conditions':<15}")
        lines.append("-" * 56)
        
        daily = data.get("daily", [])
        for day in daily:
            date_str = day.get("date", "")[:10]
            max_temp = f"{day.get('temperature_max', '--')}°"
            min_temp = f"{day.get('temperature_min', '--')}°"
            precip = f"{day.get('precipitation_sum', 0):.1f}mm"
            code = day.get("weather_code", 0)
            conditions = self._get_condition_text(code)
            lines.append(f"{date_str:<15} {max_temp:<8} {min_temp:<8} {precip:<10} {conditions:<15}")
        
        # Add simple temperature chart
        lines.append("")
        lines.append("TEMPERATURE TREND")
        lines.append("")
        lines.extend(self._create_text_chart(daily))
        
        return lines
    
    def _get_condition_text(self, code: int) -> str:
        """Get text description for weather code."""
        conditions = {
            0: "Clear",
            1: "Mostly Clear",
            2: "Partly Cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Fog",
            51: "Light Drizzle",
            53: "Drizzle",
            55: "Heavy Drizzle",
            61: "Light Rain",
            63: "Rain",
            65: "Heavy Rain",
            71: "Light Snow",
            73: "Snow",
            75: "Heavy Snow",
            80: "Rain Showers",
            81: "Heavy Showers",
            82: "Violent Showers",
            95: "Thunderstorm",
            96: "T-Storm + Hail",
            99: "Severe T-Storm"
        }
        return conditions.get(code, "Unknown")
    
    def _create_text_chart(self, daily: List[Dict[str, Any]]) -> List[str]:
        """Create a simple text-based temperature chart."""
        if not daily:
            return ["No data available"]
        
        lines = []
        max_temps = [d.get("temperature_max", 0) for d in daily]
        min_temps = [d.get("temperature_min", 0) for d in daily]
        
        if not max_temps:
            return lines
        
        chart_max = max(max_temps) + 5
        chart_min = min(min_temps) - 5
        chart_range = max(chart_max - chart_min, 1)
        chart_height = 10
        
        # Create chart rows
        for row in range(chart_height, -1, -1):
            threshold = chart_min + (row / chart_height) * chart_range
            line = f"{threshold:5.0f}° |"
            
            for i, (max_t, min_t) in enumerate(zip(max_temps, min_temps)):
                if max_t >= threshold > min_t:
                    line += " ▓▓ "
                elif max_t >= threshold and min_t >= threshold:
                    line += " ██ "
                else:
                    line += "    "
            
            lines.append(line)
        
        # X-axis
        lines.append("       +" + "----" * len(daily))
        
        # Day labels
        label_line = "       "
        for day in daily:
            date = day.get("date", "")
            if date:
                label_line += f" {date[8:10]} "
            else:
                label_line += "    "
        lines.append(label_line)
        
        return lines
    
    def _create_simple_pdf(self, content: str) -> bytes:
        """
        Create a minimal PDF structure.
        
        This creates a valid PDF with the content as text.
        For production, use a proper library like reportlab.
        """
        # Escape special characters
        content_escaped = content.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        
        # PDF structure
        pdf_lines = [
            "%PDF-1.4",
            "1 0 obj",
            "<<",
            "/Type /Catalog",
            "/Pages 2 0 R",
            ">>",
            "endobj",
            "2 0 obj",
            "<<",
            "/Type /Pages",
            "/Kids [3 0 R]",
            "/Count 1",
            ">>",
            "endobj",
            "3 0 obj",
            "<<",
            "/Type /Page",
            "/Parent 2 0 R",
            "/MediaBox [0 0 612 792]",
            "/Contents 4 0 R",
            "/Resources <<",
            "/Font <<",
            "/F1 5 0 R",
            ">>",
            ">>",
            ">>",
            "endobj",
            "4 0 obj",
            "<<",
            "/Length 6 0 R",
            ">>",
            "stream",
        ]
        
        # Build content stream
        stream_content = "BT\n"
        stream_content += "/F1 9 Tf\n"
        y = 750
        
        for line in content.split("\n"):
            if y < 50:
                break
            # Escape line for PDF
            safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_content += f"1 0 0 1 50 {y} Tm\n"
            stream_content += f"({safe_line}) Tj\n"
            y -= 12
        
        stream_content += "ET\n"
        
        pdf_lines.append(stream_content)
        pdf_lines.extend([
            "endstream",
            "endobj",
            f"6 0 obj",
            f"{len(stream_content)}",
            "endobj",
            "5 0 obj",
            "<<",
            "/Type /Font",
            "/Subtype /Type1",
            "/BaseFont /Courier",
            ">>",
            "endobj",
            "xref",
            "0 7",
            "0000000000 65535 f ",
            "0000000009 00000 n ",
            "0000000058 00000 n ",
            "0000000115 00000 n ",
            "0000000266 00000 n ",
            "0000000400 00000 n ",
            "0000000480 00000 n ",
            "trailer",
            "<<",
            "/Size 7",
            "/Root 1 0 R",
            ">>",
            "startxref",
            "500",
            "%%EOF"
        ])
        
        return "\n".join(pdf_lines).encode("latin-1")
