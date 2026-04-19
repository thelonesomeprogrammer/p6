import type React from "react";
import { useEffect, useState, useCallback } from "react";
import { socket } from "../socket";
import { ScrewCore, type PredictionResult } from "./ScrewCore";

export const ScrewFetch: React.FC<{ className?: string }> = ({
	className = "",
}) => {
	const [prediction, setPrediction] = useState<PredictionResult | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);
	const [error, setError] = useState<string | null>(null);
	const [modelType] = useState<string>("rf");

	const fetchPrediction = useCallback(
		async (signal?: AbortSignal) => {
			setIsLoading(true);
			setError(null);
			try {
				const res = await fetch(
					`http://localhost:5000/predict_all?model=${modelType}`,
					{ signal },
				);
				const data = await res.json();
				if (data.error) {
					setError(data.error);
					setPrediction(null);
				} else if (data.predictions && data.predictions.length > 0) {
					const lastPred = data.predictions[data.predictions.length - 1];
					if (
						lastPred.prediction &&
						typeof lastPred.prediction === "object"
					) {
						setPrediction(lastPred.prediction);
					} else if (
						lastPred.classification &&
						typeof lastPred.classification === "object"
					) {
						setPrediction({
							...lastPred,
							prediction: lastPred.classification.prediction || "M",
							probabilities: lastPred.classification.probabilities || {},
						});
					} else {
						setPrediction(lastPred);
					}
				} else {
					setPrediction(null);
				}
			} catch (e: any) {
				if (e.name === "AbortError") return;
				setError("Failed to connect to backend");
				console.error(e);
			} finally {
				setIsLoading(false);
			}
		},
		[modelType],
	);

	useEffect(() => {
		const controller = new AbortController();
		const onRunFinished = () => fetchPrediction(controller.signal);
		socket.on("runFinished", onRunFinished);
		return () => {
			socket.off("runFinished", onRunFinished);
			controller.abort();
		};
	}, [fetchPrediction]);

	useEffect(() => {
		fetchPrediction();
	}, [fetchPrediction]);

	return (
		<ScrewCore
			prediction={prediction}
			isLoading={isLoading}
			error={error}
			className={className}
		/>
	);
};

export default ScrewFetch;
