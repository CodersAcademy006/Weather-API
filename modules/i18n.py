"""
Internationalization (i18n) Service Module

Provides multi-language support for the IntelliWeather API.
Supported languages: English (en), Hindi (hi), Urdu (ur), Arabic (ar), Spanish (es)
"""

import json
import os
from typing import Dict, Optional, Any
from functools import lru_cache

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)


# Default translations (embedded for reliability)
DEFAULT_TRANSLATIONS = {
    "en": {
        "app_name": "IntelliWeather",
        "tagline": "Your Premium Weather Companion",
        "current_weather": "Current Weather",
        "hourly_forecast": "Hourly Forecast",
        "daily_forecast": "7-Day Forecast",
        "feels_like": "Feels Like",
        "humidity": "Humidity",
        "wind": "Wind",
        "pressure": "Pressure",
        "uv_index": "UV Index",
        "air_quality": "Air Quality",
        "precipitation": "Precipitation",
        "sunrise": "Sunrise",
        "sunset": "Sunset",
        "search_placeholder": "Search for a city...",
        "loading": "Loading...",
        "error": "Error",
        "retry": "Retry",
        "connected": "Connected",
        "disconnected": "Disconnected",
        "connecting": "Connecting",
        "sign_in": "Sign In",
        "sign_up": "Sign Up",
        "sign_out": "Sign Out",
        "email": "Email",
        "password": "Password",
        "welcome_back": "Welcome Back",
        "create_account": "Create Account",
        "dark_mode": "Dark Mode",
        "light_mode": "Light Mode",
        "language": "Language",
        "settings": "Settings",
        "alerts": "Weather Alerts",
        "no_alerts": "No active weather alerts",
        "severe_weather": "Severe Weather Warning",
        "download_report": "Download Report",
        "pdf": "PDF",
        "excel": "Excel",
        # Weather conditions
        "clear_sky": "Clear Sky",
        "partly_cloudy": "Partly Cloudy",
        "cloudy": "Cloudy",
        "overcast": "Overcast",
        "fog": "Fog",
        "drizzle": "Drizzle",
        "rain": "Rain",
        "heavy_rain": "Heavy Rain",
        "snow": "Snow",
        "heavy_snow": "Heavy Snow",
        "thunderstorm": "Thunderstorm",
        # Days of week
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
        # Error messages
        "error_fetch_weather": "Failed to fetch weather data",
        "error_location": "Unable to get your location",
        "error_invalid_city": "City not found",
        "error_rate_limit": "Too many requests. Please try again later.",
        "error_server": "Server error. Please try again."
    },
    "hi": {
        "app_name": "इंटेलीवेदर",
        "tagline": "आपका प्रीमियम मौसम साथी",
        "current_weather": "वर्तमान मौसम",
        "hourly_forecast": "प्रति घंटा पूर्वानुमान",
        "daily_forecast": "7-दिन का पूर्वानुमान",
        "feels_like": "अनुभव",
        "humidity": "आर्द्रता",
        "wind": "हवा",
        "pressure": "दबाव",
        "uv_index": "यूवी सूचकांक",
        "air_quality": "वायु गुणवत्ता",
        "precipitation": "वर्षा",
        "sunrise": "सूर्योदय",
        "sunset": "सूर्यास्त",
        "search_placeholder": "शहर खोजें...",
        "loading": "लोड हो रहा है...",
        "error": "त्रुटि",
        "retry": "पुनः प्रयास करें",
        "connected": "कनेक्ट",
        "disconnected": "डिस्कनेक्ट",
        "connecting": "कनेक्ट हो रहा है",
        "sign_in": "साइन इन",
        "sign_up": "साइन अप",
        "sign_out": "साइन आउट",
        "email": "ईमेल",
        "password": "पासवर्ड",
        "welcome_back": "वापसी पर स्वागत है",
        "create_account": "खाता बनाएं",
        "dark_mode": "डार्क मोड",
        "light_mode": "लाइट मोड",
        "language": "भाषा",
        "settings": "सेटिंग्स",
        "alerts": "मौसम अलर्ट",
        "no_alerts": "कोई सक्रिय मौसम अलर्ट नहीं",
        "severe_weather": "गंभीर मौसम चेतावनी",
        "download_report": "रिपोर्ट डाउनलोड करें",
        "pdf": "पीडीएफ",
        "excel": "एक्सेल",
        "clear_sky": "साफ आसमान",
        "partly_cloudy": "आंशिक बादल",
        "cloudy": "बादल",
        "overcast": "घनघोर बादल",
        "fog": "कोहरा",
        "drizzle": "बूंदाबांदी",
        "rain": "बारिश",
        "heavy_rain": "भारी बारिश",
        "snow": "बर्फ",
        "heavy_snow": "भारी बर्फ",
        "thunderstorm": "तूफान",
        "monday": "सोमवार",
        "tuesday": "मंगलवार",
        "wednesday": "बुधवार",
        "thursday": "गुरुवार",
        "friday": "शुक्रवार",
        "saturday": "शनिवार",
        "sunday": "रविवार",
        "error_fetch_weather": "मौसम डेटा प्राप्त करने में विफल",
        "error_location": "आपका स्थान प्राप्त करने में असमर्थ",
        "error_invalid_city": "शहर नहीं मिला",
        "error_rate_limit": "बहुत सारे अनुरोध। कृपया बाद में पुनः प्रयास करें।",
        "error_server": "सर्वर त्रुटि। कृपया पुनः प्रयास करें।"
    },
    "ur": {
        "app_name": "انٹیلی ویدر",
        "tagline": "آپ کا پریمیم موسم ساتھی",
        "current_weather": "موجودہ موسم",
        "hourly_forecast": "گھنٹہ وار پیشگوئی",
        "daily_forecast": "7 دن کی پیشگوئی",
        "feels_like": "محسوس",
        "humidity": "نمی",
        "wind": "ہوا",
        "pressure": "دباؤ",
        "uv_index": "یو وی انڈیکس",
        "air_quality": "ہوا کا معیار",
        "precipitation": "بارش",
        "sunrise": "طلوع آفتاب",
        "sunset": "غروب آفتاب",
        "search_placeholder": "شہر تلاش کریں...",
        "loading": "لوڈ ہو رہا ہے...",
        "error": "غلطی",
        "retry": "دوبارہ کوشش کریں",
        "connected": "منسلک",
        "disconnected": "منقطع",
        "connecting": "جڑ رہا ہے",
        "sign_in": "سائن ان",
        "sign_up": "سائن اپ",
        "sign_out": "سائن آؤٹ",
        "email": "ای میل",
        "password": "پاس ورڈ",
        "welcome_back": "واپسی پر خوش آمدید",
        "create_account": "اکاؤنٹ بنائیں",
        "dark_mode": "ڈارک موڈ",
        "light_mode": "لائٹ موڈ",
        "language": "زبان",
        "settings": "ترتیبات",
        "alerts": "موسمی الرٹس",
        "no_alerts": "کوئی فعال موسمی الرٹ نہیں",
        "severe_weather": "شدید موسم کی وارننگ",
        "download_report": "رپورٹ ڈاؤن لوڈ کریں",
        "pdf": "پی ڈی ایف",
        "excel": "ایکسل",
        "clear_sky": "صاف آسمان",
        "partly_cloudy": "جزوی بادل",
        "cloudy": "بادل",
        "overcast": "گھنے بادل",
        "fog": "دھند",
        "drizzle": "ہلکی بارش",
        "rain": "بارش",
        "heavy_rain": "تیز بارش",
        "snow": "برف",
        "heavy_snow": "بھاری برف",
        "thunderstorm": "طوفان",
        "monday": "پیر",
        "tuesday": "منگل",
        "wednesday": "بدھ",
        "thursday": "جمعرات",
        "friday": "جمعہ",
        "saturday": "ہفتہ",
        "sunday": "اتوار",
        "error_fetch_weather": "موسم کا ڈیٹا حاصل کرنے میں ناکام",
        "error_location": "آپ کا مقام حاصل کرنے میں ناکام",
        "error_invalid_city": "شہر نہیں ملا",
        "error_rate_limit": "بہت زیادہ درخواستیں۔ براہ کرم بعد میں دوبارہ کوشش کریں۔",
        "error_server": "سرور کی غلطی۔ براہ کرم دوبارہ کوشش کریں۔"
    },
    "ar": {
        "app_name": "إنتلي ويذر",
        "tagline": "رفيقك المميز للطقس",
        "current_weather": "الطقس الحالي",
        "hourly_forecast": "التوقعات بالساعة",
        "daily_forecast": "توقعات 7 أيام",
        "feels_like": "يشعر مثل",
        "humidity": "الرطوبة",
        "wind": "الرياح",
        "pressure": "الضغط",
        "uv_index": "مؤشر الأشعة فوق البنفسجية",
        "air_quality": "جودة الهواء",
        "precipitation": "الهطول",
        "sunrise": "شروق الشمس",
        "sunset": "غروب الشمس",
        "search_placeholder": "ابحث عن مدينة...",
        "loading": "جار التحميل...",
        "error": "خطأ",
        "retry": "إعادة المحاولة",
        "connected": "متصل",
        "disconnected": "غير متصل",
        "connecting": "جار الاتصال",
        "sign_in": "تسجيل الدخول",
        "sign_up": "إنشاء حساب",
        "sign_out": "تسجيل الخروج",
        "email": "البريد الإلكتروني",
        "password": "كلمة المرور",
        "welcome_back": "مرحباً بعودتك",
        "create_account": "إنشاء حساب",
        "dark_mode": "الوضع الداكن",
        "light_mode": "الوضع الفاتح",
        "language": "اللغة",
        "settings": "الإعدادات",
        "alerts": "تنبيهات الطقس",
        "no_alerts": "لا توجد تنبيهات طقس نشطة",
        "severe_weather": "تحذير من طقس شديد",
        "download_report": "تحميل التقرير",
        "pdf": "بي دي إف",
        "excel": "إكسل",
        "clear_sky": "سماء صافية",
        "partly_cloudy": "غائم جزئياً",
        "cloudy": "غائم",
        "overcast": "ملبد بالغيوم",
        "fog": "ضباب",
        "drizzle": "رذاذ",
        "rain": "مطر",
        "heavy_rain": "أمطار غزيرة",
        "snow": "ثلج",
        "heavy_snow": "ثلج كثيف",
        "thunderstorm": "عاصفة رعدية",
        "monday": "الإثنين",
        "tuesday": "الثلاثاء",
        "wednesday": "الأربعاء",
        "thursday": "الخميس",
        "friday": "الجمعة",
        "saturday": "السبت",
        "sunday": "الأحد",
        "error_fetch_weather": "فشل في جلب بيانات الطقس",
        "error_location": "تعذر الحصول على موقعك",
        "error_invalid_city": "المدينة غير موجودة",
        "error_rate_limit": "طلبات كثيرة جداً. يرجى المحاولة لاحقاً.",
        "error_server": "خطأ في الخادم. يرجى المحاولة مرة أخرى."
    },
    "es": {
        "app_name": "IntelliWeather",
        "tagline": "Tu compañero premium del clima",
        "current_weather": "Clima Actual",
        "hourly_forecast": "Pronóstico por Hora",
        "daily_forecast": "Pronóstico de 7 Días",
        "feels_like": "Sensación Térmica",
        "humidity": "Humedad",
        "wind": "Viento",
        "pressure": "Presión",
        "uv_index": "Índice UV",
        "air_quality": "Calidad del Aire",
        "precipitation": "Precipitación",
        "sunrise": "Amanecer",
        "sunset": "Atardecer",
        "search_placeholder": "Buscar una ciudad...",
        "loading": "Cargando...",
        "error": "Error",
        "retry": "Reintentar",
        "connected": "Conectado",
        "disconnected": "Desconectado",
        "connecting": "Conectando",
        "sign_in": "Iniciar Sesión",
        "sign_up": "Registrarse",
        "sign_out": "Cerrar Sesión",
        "email": "Correo Electrónico",
        "password": "Contraseña",
        "welcome_back": "Bienvenido de Nuevo",
        "create_account": "Crear Cuenta",
        "dark_mode": "Modo Oscuro",
        "light_mode": "Modo Claro",
        "language": "Idioma",
        "settings": "Configuración",
        "alerts": "Alertas del Clima",
        "no_alerts": "Sin alertas activas del clima",
        "severe_weather": "Advertencia de Clima Severo",
        "download_report": "Descargar Informe",
        "pdf": "PDF",
        "excel": "Excel",
        "clear_sky": "Cielo Despejado",
        "partly_cloudy": "Parcialmente Nublado",
        "cloudy": "Nublado",
        "overcast": "Cubierto",
        "fog": "Niebla",
        "drizzle": "Llovizna",
        "rain": "Lluvia",
        "heavy_rain": "Lluvia Intensa",
        "snow": "Nieve",
        "heavy_snow": "Nevada Intensa",
        "thunderstorm": "Tormenta Eléctrica",
        "monday": "Lunes",
        "tuesday": "Martes",
        "wednesday": "Miércoles",
        "thursday": "Jueves",
        "friday": "Viernes",
        "saturday": "Sábado",
        "sunday": "Domingo",
        "error_fetch_weather": "Error al obtener datos del clima",
        "error_location": "No se pudo obtener tu ubicación",
        "error_invalid_city": "Ciudad no encontrada",
        "error_rate_limit": "Demasiadas solicitudes. Por favor, intenta más tarde.",
        "error_server": "Error del servidor. Por favor, intenta de nuevo."
    }
}


class I18nService:
    """
    Internationalization service for multi-language support.
    
    Features:
    - Translation lookup with fallback to English
    - Dynamic language switching
    - JSON translation file support
    """
    
    def __init__(self):
        """Initialize the i18n service."""
        self._translations: Dict[str, Dict[str, str]] = DEFAULT_TRANSLATIONS.copy()
        self._default_lang = settings.DEFAULT_LANGUAGE
        self._load_translation_files()
        logger.info(f"I18n service initialized with languages: {list(self._translations.keys())}")
    
    def _load_translation_files(self) -> None:
        """Load translation files from i18n directory."""
        i18n_dir = os.path.join(os.path.dirname(__file__), "..", "i18n")
        
        if not os.path.exists(i18n_dir):
            logger.debug("No i18n directory found, using embedded translations")
            return
        
        for lang in settings.SUPPORTED_LANGUAGES:
            filepath = os.path.join(i18n_dir, f"{lang}.json")
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        file_translations = json.load(f)
                        # Merge with defaults (file takes precedence)
                        if lang in self._translations:
                            self._translations[lang].update(file_translations)
                        else:
                            self._translations[lang] = file_translations
                    logger.debug(f"Loaded translation file: {filepath}")
                except Exception as e:
                    logger.warning(f"Failed to load translation file {filepath}: {e}")
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        return list(self._translations.keys())
    
    def translate(
        self,
        key: str,
        lang: str = None,
        **kwargs
    ) -> str:
        """
        Translate a key to the specified language.
        
        Args:
            key: Translation key
            lang: Target language code
            **kwargs: Format arguments for the translation
            
        Returns:
            Translated string, or key if not found
        """
        lang = lang or self._default_lang
        
        # Try requested language
        if lang in self._translations:
            value = self._translations[lang].get(key)
            if value:
                if kwargs:
                    try:
                        return value.format(**kwargs)
                    except KeyError:
                        return value
                return value
        
        # Fallback to default language
        if lang != self._default_lang and self._default_lang in self._translations:
            value = self._translations[self._default_lang].get(key)
            if value:
                if kwargs:
                    try:
                        return value.format(**kwargs)
                    except KeyError:
                        return value
                return value
        
        # Return key if not found
        return key
    
    def get_all_translations(self, lang: str = None) -> Dict[str, str]:
        """Get all translations for a language."""
        lang = lang or self._default_lang
        return self._translations.get(lang, self._translations.get(self._default_lang, {}))
    
    def get_weather_description(self, weather_code: int, lang: str = None) -> str:
        """
        Get weather description for a WMO weather code.
        
        Args:
            weather_code: WMO weather code
            lang: Target language
            
        Returns:
            Human-readable weather description
        """
        # WMO weather code mapping
        code_map = {
            0: "clear_sky",
            1: "partly_cloudy",
            2: "partly_cloudy",
            3: "overcast",
            45: "fog",
            48: "fog",
            51: "drizzle",
            53: "drizzle",
            55: "drizzle",
            61: "rain",
            63: "rain",
            65: "heavy_rain",
            71: "snow",
            73: "snow",
            75: "heavy_snow",
            77: "snow",
            80: "rain",
            81: "rain",
            82: "heavy_rain",
            85: "snow",
            86: "heavy_snow",
            95: "thunderstorm",
            96: "thunderstorm",
            99: "thunderstorm"
        }
        
        key = code_map.get(weather_code, "partly_cloudy")
        return self.translate(key, lang)


# Global service instance
_i18n_service: Optional[I18nService] = None


def get_i18n_service() -> I18nService:
    """Get the global i18n service instance."""
    global _i18n_service
    if _i18n_service is None:
        _i18n_service = I18nService()
    return _i18n_service


def translate(key: str, lang: str = None, **kwargs) -> str:
    """Convenience function for translation."""
    return get_i18n_service().translate(key, lang, **kwargs)
