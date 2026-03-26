import httpx
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

@router.get("/weather")
async def get_weather(
    lat: float = Query(..., description="Latitude of the location"),
    lng: float = Query(..., description="Longitude of the location")
):
    """
    Fetch weather forecast from Open-Meteo.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Using parameters exactly matching user specs
            r = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "timezone": "Asia/Kolkata"
                }
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch weather data: {str(e)}")

@router.get("/solar")
async def get_solar_pv(
    lat: float = Query(..., description="Latitude of the location"),
    lng: float = Query(..., description="Longitude of the location")
):
    """
    Fetch PV calculation from EU JRC.
    """
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc",
                params={
                    "lat": lat,
                    "lon": lng,
                    "peakpower": 1,
                    "loss": 14,
                    "outputformat": "json"
                }
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch solar PV data: {str(e)}")
