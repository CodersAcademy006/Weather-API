"""
Internationalization (i18n) Routes

Provides endpoints for translation management and language selection.
"""

from typing import Dict, List

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field

from config import settings
from logging_config import get_logger
from modules.i18n import get_i18n_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/i18n",
    tags=["Internationalization"],
)


class TranslationsResponse(BaseModel):
    """Response model for translations."""
    language: str = Field(..., description="Language code")
    translations: Dict[str, str] = Field(..., description="Translation key-value pairs")


class SupportedLanguagesResponse(BaseModel):
    """Response model for supported languages."""
    languages: List[str] = Field(..., description="List of supported language codes")
    default: str = Field(..., description="Default language code")


@router.get(
    "/languages",
    response_model=SupportedLanguagesResponse,
    summary="Get supported languages",
    description="Get a list of all supported language codes."
)
async def get_supported_languages(request: Request):
    """Get list of supported languages."""
    i18n = get_i18n_service()
    
    return SupportedLanguagesResponse(
        languages=i18n.get_supported_languages(),
        default=settings.DEFAULT_LANGUAGE
    )


@router.get(
    "/translations",
    response_model=TranslationsResponse,
    summary="Get translations for a language",
    description="""
    Get all UI translations for a specific language.
    
    **Supported languages:**
    - en: English (default)
    - hi: Hindi
    - ur: Urdu
    - ar: Arabic
    - es: Spanish
    """
)
async def get_translations(
    request: Request,
    lang: str = Query(None, description="Language code (defaults to en)")
):
    """Get translations for a language."""
    i18n = get_i18n_service()
    language = lang or settings.DEFAULT_LANGUAGE
    
    if language not in i18n.get_supported_languages():
        language = settings.DEFAULT_LANGUAGE
    
    translations = i18n.get_all_translations(language)
    
    return TranslationsResponse(
        language=language,
        translations=translations
    )


@router.get(
    "/translate",
    summary="Translate a single key",
    description="Translate a single key to the specified language."
)
async def translate_key(
    request: Request,
    key: str = Query(..., description="Translation key"),
    lang: str = Query(None, description="Language code")
):
    """Translate a single key."""
    i18n = get_i18n_service()
    language = lang or settings.DEFAULT_LANGUAGE
    
    translation = i18n.translate(key, language)
    
    return {
        "key": key,
        "language": language,
        "translation": translation
    }


@router.get(
    "/weather-description",
    summary="Get localized weather description",
    description="Get a human-readable weather description for a WMO weather code."
)
async def get_weather_description(
    request: Request,
    code: int = Query(..., ge=0, le=99, description="WMO weather code"),
    lang: str = Query(None, description="Language code")
):
    """Get localized weather description for a weather code."""
    i18n = get_i18n_service()
    language = lang or settings.DEFAULT_LANGUAGE
    
    description = i18n.get_weather_description(code, language)
    
    return {
        "weather_code": code,
        "language": language,
        "description": description
    }
