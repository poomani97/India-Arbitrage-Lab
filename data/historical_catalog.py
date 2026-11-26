
from typing import Any, Dict, List, Optional


class HistoricalDataCatalog:

    def __init__(self):
        self.datasets: Dict[str, Dict[str, Any]] = {}

    def register(
        dataset_id: str,
        file_path: str,
        symbol: str,
        timeframe: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:

        if not dataset_id:
            raise ValueError("Dataset ID cannot be empty")

        if not file_path:
            raise ValueError("File path cannot be empty")

        self.datasets[dataset_id] = {
            "dataset_id": dataset_id,
            "file_path": file_path,
            "symbol": symbol,
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "source": source,
            "quality_status": "UNCHECKED",
            "quality_report": None,
        }

        return True

    def get(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        return self.datasets.get(dataset_id)

    def remove(self, dataset_id: str) -> bool:
        if dataset_id not in self.datasets:
            return False

        del self.datasets[dataset_id]
        return True

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self.datasets.values())

    def list_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        return [
            dataset
            for dataset in self.datasets.values()
            if dataset["symbol"].upper() == symbol.upper()
        ]

    def list_by_timeframe(self, timeframe: str) -> List[Dict[str, Any]]:
        return [
            dataset
            for dataset in self.datasets.values()
            if dataset["timeframe"].lower() == timeframe.lower()
        ]

    def update_quality(
        self,
        dataset_id: str,
        status: str,
        report: Optional[Dict[str, Any]] = None,
    ) -> bool:

        if dataset_id not in self.datasets:
            return False

        self.datasets[dataset_id]["quality_status"] = status
        self.datasets[dataset_id]["quality_report"] = report

        return True

    def count(self) -> int:
        return len(self.datasets)

    def clear(self) -> None:
        self.datasets.clear()

    def summary(self) -> Dict[str, Any]:
        statuses = {}

        for dataset in self.datasets.values():
            status = dataset["quality_status"]
            statuses[status] = statuses.get(status, 0) + 1

        return {
            "total_datasets": self.count(),
            "quality_status_counts": statuses,
            "symbols": sorted(
                set(
                    dataset["symbol"]
                    for dataset in self.datasets.values()
                )
            ),
            "timeframes": sorted(
                set(
                    dataset["timeframe"]
                    for dataset in self.datasets.values()
                )
            ),
        }
      
