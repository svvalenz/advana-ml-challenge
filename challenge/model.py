import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Union, List
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

class DelayModel:

    def __init__(
        self
    ):
        self._model = None # Model should be saved in this attribute.
        self._label_encoders = {}  # Store label encoders for categorical features
        self._feature_columns = [
            "OPERA_Latin American Wings", 
            "MES_7",
            "MES_10",
            "OPERA_Grupo LATAM",
            "MES_12",
            "TIPOVUELO_I",
            "MES_4",
            "MES_11",
            "OPERA_Sky Airline",
            "OPERA_Copa Air"
        ]

    def _get_period_day(self, date: str) -> str:
        """Get period of day based on time."""
        date_time = datetime.strptime(date, '%Y-%m-%d %H:%M:%S').time()
        morning_min = datetime.strptime("05:00", '%H:%M').time()
        morning_max = datetime.strptime("11:59", '%H:%M').time()
        afternoon_min = datetime.strptime("12:00", '%H:%M').time()
        afternoon_max = datetime.strptime("18:59", '%H:%M').time()
        evening_min = datetime.strptime("19:00", '%H:%M').time()
        evening_max = datetime.strptime("23:59", '%H:%M').time()
        night_min = datetime.strptime("00:00", '%H:%M').time()
        night_max = datetime.strptime("4:59", '%H:%M').time()
        
        if date_time > morning_min and date_time < morning_max:
            return 'mañana'
        elif date_time > afternoon_min and date_time < afternoon_max:
            return 'tarde'
        elif ((date_time > evening_min and date_time < evening_max) or
              (date_time > night_min and date_time < night_max)):
            return 'noche'

    def _is_high_season(self, fecha: str) -> int:
        """Check if date is in high season."""
        fecha_año = int(fecha.split('-')[0])
        fecha = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
        range1_min = datetime.strptime('15-Dec', '%d-%b').replace(year=fecha_año)
        range1_max = datetime.strptime('31-Dec', '%d-%b').replace(year=fecha_año)
        range2_min = datetime.strptime('1-Jan', '%d-%b').replace(year=fecha_año)
        range2_max = datetime.strptime('3-Mar', '%d-%b').replace(year=fecha_año)
        range3_min = datetime.strptime('15-Jul', '%d-%b').replace(year=fecha_año)
        range3_max = datetime.strptime('31-Jul', '%d-%b').replace(year=fecha_año)
        range4_min = datetime.strptime('11-Sep', '%d-%b').replace(year=fecha_año)
        range4_max = datetime.strptime('30-Sep', '%d-%b').replace(year=fecha_año)
        
        if ((fecha >= range1_min and fecha <= range1_max) or 
            (fecha >= range2_min and fecha <= range2_max) or 
            (fecha >= range3_min and fecha <= range3_max) or
            (fecha >= range4_min and fecha <= range4_max)):
            return 1
        else:
            return 0

    def _get_min_diff(self, row: pd.Series) -> float:
        """Calculate difference in minutes between scheduled and actual departure."""
        fecha_o = datetime.strptime(row['Fecha-O'], '%Y-%m-%d %H:%M:%S')
        fecha_i = datetime.strptime(row['Fecha-I'], '%Y-%m-%d %H:%M:%S')
        min_diff = ((fecha_o - fecha_i).total_seconds()) / 60
        return min_diff

    def preprocess(
        self,
        data: pd.DataFrame,
        target_column: str = None
    ) -> Union[Tuple[pd.DataFrame, pd.DataFrame], pd.DataFrame]:
        """
        Prepare raw data for training or predict.

        Args:
            data (pd.DataFrame): raw data.
            target_column (str, optional): if set, the target is returned.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: features and target.
            or
            pd.DataFrame: features.
        """
        # Create a copy to avoid modifying original data
        data_processed = data.copy()
        
        # Generate features
        data_processed['period_day'] = data_processed['Fecha-I'].apply(self._get_period_day)
        data_processed['high_season'] = data_processed['Fecha-I'].apply(self._is_high_season)
        data_processed['min_diff'] = data_processed.apply(self._get_min_diff, axis=1)
        
        # Create delay target if target_column is specified
        if target_column is not None:
            threshold_in_minutes = 15
            data_processed['delay'] = np.where(data_processed['min_diff'] > threshold_in_minutes, 1, 0)
        
        # Feature engineering: One-hot encoding for categorical variables
        # OPERA (airline) one-hot encoding
        opera_dummies = pd.get_dummies(data_processed['OPERA'], prefix='OPERA')
        
        # MES (month) one-hot encoding
        mes_dummies = pd.get_dummies(data_processed['MES'], prefix='MES')
        
        # TIPOVUELO (flight type) one-hot encoding
        tipovuelo_dummies = pd.get_dummies(data_processed['TIPOVUELO'], prefix='TIPOVUELO')
        
        # Combine all features
        features = pd.concat([opera_dummies, mes_dummies, tipovuelo_dummies], axis=1)
        
        # Select only the top 10 features as determined in the notebook
        features = features.reindex(columns=self._feature_columns, fill_value=0)
        
        if target_column is not None:
            target = data_processed[[target_column]]
            return features, target
        else:
            return features

    def fit(
        self,
        features: pd.DataFrame,
        target: pd.DataFrame
    ) -> None:
        """
        Fit model with preprocessed data.

        Args:
            features (pd.DataFrame): preprocessed data.
            target (pd.DataFrame): target.
        """
        # Calculate class weights for balancing
        n_y0 = len(target[target['delay'] == 0])
        n_y1 = len(target[target['delay'] == 1])
        
        # Use Logistic Regression with class balancing as determined in the notebook
        self._model = LogisticRegression(
            class_weight={1: n_y0/len(target), 0: n_y1/len(target)},
            random_state=42
        )
        
        # Fit the model
        self._model.fit(features, target.values.ravel())

    def predict(
        self,
        features: pd.DataFrame
    ) -> List[int]:
        """
        Predict delays for new flights.

        Args:
            features (pd.DataFrame): preprocessed data.
        
        Returns:
            (List[int]): predicted targets.
        """
        if self._model is None:
            raise ValueError("Model has not been fitted yet. Call fit() first.")
        
        predictions = self._model.predict(features)
        return predictions.tolist()