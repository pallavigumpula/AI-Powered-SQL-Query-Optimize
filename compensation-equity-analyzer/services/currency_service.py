"""
Currency Normalization Service
Converts compensation into base currency (USD) using effective-dated exchange rates.
Flags missing conversion rates explicitly rather than hallucinating or assuming a rate.
"""

from datetime import date
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from models.supporting import CurrencyExchangeRate, DataQualityIssue
from config import settings

class CurrencyService:
    def __init__(self, db: Session):
        self.db = db
        self.base_currency = settings.BASE_CURRENCY

    def get_exchange_rate(self, from_currency: str, to_currency: Optional[str] = None, as_of_date: Optional[date] = None) -> Optional[float]:
        """
        Retrieves effective exchange rate for the given currency pair and date.
        Returns None if missing.
        """
        target_currency = to_currency or self.base_currency
        if from_currency == target_currency:
            return 1.0

        target_date = as_of_date or date.today()

        rate_record = self.db.query(CurrencyExchangeRate).filter(
            CurrencyExchangeRate.from_currency == from_currency,
            CurrencyExchangeRate.to_currency == target_currency,
            CurrencyExchangeRate.effective_from <= target_date,
            CurrencyExchangeRate.effective_to >= target_date
        ).first()

        if rate_record:
            return rate_record.rate
        
        # Check inverse rate
        inverse_record = self.db.query(CurrencyExchangeRate).filter(
            CurrencyExchangeRate.from_currency == target_currency,
            CurrencyExchangeRate.to_currency == from_currency,
            CurrencyExchangeRate.effective_from <= target_date,
            CurrencyExchangeRate.effective_to >= target_date
        ).first()

        if inverse_record and inverse_record.rate > 0:
            return 1.0 / inverse_record.rate

        return None

    def convert_to_base(self, amount: float, from_currency: str, as_of_date: Optional[date] = None, record_id: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]:
        """
        Converts amount from given currency to base currency (USD).
        Returns:
            (converted_amount, error_message)
            If exchange rate is missing, returns (None, "MISSING_EXCHANGE_RATE").
        """
        if from_currency == self.base_currency:
            return amount, None

        rate = self.get_exchange_rate(from_currency, self.base_currency, as_of_date)
        if rate is None:
            # Mandatory Edge Case 3: Flag missing currency conversion
            error_msg = f"Missing exchange rate from {from_currency} to {self.base_currency} for date {as_of_date or date.today()}"
            if record_id:
                # Log Data Quality Issue if not already open
                existing_issue = self.db.query(DataQualityIssue).filter(
                    DataQualityIssue.issue_type == "MISSING_EXCHANGE_RATE",
                    DataQualityIssue.entity_id == record_id,
                    DataQualityIssue.status == "OPEN"
                ).first()
                if not existing_issue:
                    issue = DataQualityIssue(
                        id=f"DQI-FX-{record_id}",
                        issue_type="MISSING_EXCHANGE_RATE",
                        severity="CRITICAL",
                        entity_type="SalaryRecord",
                        entity_id=record_id,
                        description=error_msg,
                        status="OPEN",
                        ground_truth_label="CASE_3_MISSING_CURRENCY_CONVERSION"
                    )
                    self.db.add(issue)
                    self.db.commit()

            return None, "MISSING_EXCHANGE_RATE"

        converted_amount = round(amount * rate, 2)
        return converted_amount, None
