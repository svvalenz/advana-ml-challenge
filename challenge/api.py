import fastapi
import pandas as pd
from typing import List, Dict, Any
from pydantic import BaseModel, Field, validator, ValidationError
from .model import DelayModel

app = fastapi.FastAPI()

# Initialize the model globally
model = DelayModel()

# Train the model on startup
def initialize_model():
    """Initialize and train the model with the dataset"""
    try:
        # Load the dataset
        data = pd.read_csv("data/data.csv")
        
        # Preprocess and get features and target
        features, target = model.preprocess(data, target_column="delay")
        
        # Train the model
        model.fit(features, target)
        
        print("Model trained successfully!")
        
    except Exception as e:
        print(f"Error training model: {e}")
        raise

# Initialize model on startup
initialize_model()

# Exception handler for validation errors
@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return fastapi.responses.JSONResponse(
        status_code=400,
        content={"detail": "Validation error"}
    )

class FlightData(BaseModel):
    """Model for individual flight data"""
    OPERA: str = Field(..., description="Airline name")
    TIPOVUELO: str = Field(..., description="Flight type: I=International, N=National")
    MES: int = Field(..., description="Month (1-12)")

class FlightRequest(BaseModel):
    """Model for the request containing multiple flights"""
    flights: List[FlightData] = Field(..., description="List of flights to predict")

class PredictionResponse(BaseModel):
    """Model for the prediction response"""
    predict: List[int] = Field(..., description="List of delay predictions (0=no delay, 1=delay)")

# Valid airlines from the dataset
VALID_AIRLINES = {
    "Aerolineas Argentinas", "Aeromexico", "Air Canada", "Air France", 
    "Alitalia", "American Airlines", "Austral", "Avianca", "British Airways",
    "Copa Air", "Delta Air", "Gol Trans", "Grupo LATAM", "Iberia", 
    "JetSmart SPA", "K.L.M.", "Lacsa", "Latin American Wings", 
    "Oceanair Linhas Aereas", "Plus Ultra Lineas Aereas", "Qantas Airways",
    "Sky Airline", "United Airlines"
}

@app.get("/", status_code=200)
async def get_root() -> dict:
    return {
        "message": "Advana ML Challenge API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "predict": "/predict"
        }
    }

@app.get("/health", status_code=200)
async def get_health() -> dict:
    return {
        "status": "OK"
    }

@app.post("/predict", status_code=200, response_model=PredictionResponse)
async def post_predict(request: FlightRequest) -> PredictionResponse:
    """
    Predict flight delays for a list of flights.
    
    Args:
        request: FlightRequest containing a list of flights
        
    Returns:
        PredictionResponse with delay predictions
        
    Raises:
        HTTPException: If airline is not valid or other validation errors
    """
    try:
        # Validate input data
        for flight in request.flights:
            # Validate airline
            if flight.OPERA not in VALID_AIRLINES:
                raise fastapi.HTTPException(
                    status_code=400, 
                    detail=f"Invalid airline: {flight.OPERA}"
                )
            
            # Validate TIPOVUELO
            if flight.TIPOVUELO not in ['I', 'N']:
                raise fastapi.HTTPException(
                    status_code=400,
                    detail=f"Invalid TIPOVUELO: {flight.TIPOVUELO}. Must be 'I' or 'N'"
                )
            
            # Validate MES
            if flight.MES < 1 or flight.MES > 12:
                raise fastapi.HTTPException(
                    status_code=400,
                    detail=f"Invalid MES: {flight.MES}. Must be between 1 and 12"
                )
        
        # Convert to DataFrame for model processing
        flights_data = []
        for flight in request.flights:
            flights_data.append({
                'OPERA': flight.OPERA,
                'TIPOVUELO': flight.TIPOVUELO,
                'MES': flight.MES,
                # Add dummy values for required columns (these won't be used in prediction)
                'Fecha-I': '2023-01-01 10:00:00',
                'Fecha-O': '2023-01-01 10:15:00',
                'Vlo-I': 'AA100',
                'Vlo-O': 'AA100',
                'Ori-I': 'SCL',
                'Des-I': 'LIM',
                'Emp-I': 'AA',
                'Ori-O': 'SCL',
                'Des-O': 'LIM',
                'Emp-O': 'AA',
                'DIA': 1,
                'AÑO': 2023,
                'DIANOM': 'Domingo',
                'SIGLAORI': 'Santiago',
                'SIGLADES': 'Lima'
            })
        
        # Create DataFrame
        df = pd.DataFrame(flights_data)
        
        # Preprocess data
        features = model.preprocess(df)
        
        # Make predictions
        predictions = model.predict(features)
        
        return PredictionResponse(predict=predictions)
        
    except fastapi.HTTPException:
        raise
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )