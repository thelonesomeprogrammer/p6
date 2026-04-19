import type React from "react";
import { useEffect, useState } from "react";
import { socket } from "../socket";
import { ScrewCore, type PredictionResult } from "./ScrewCore";

export const ScrewSocket: React.FC<{ className?: string }> = ({
	className = "",
}) => {
	const [prediction, setPrediction] = useState<PredictionResult | null>(null);

	useEffect(() => {
		const onPrediction = (data: any) => {
			if (data.classification || data.regression) {
				let pLabel = data.classification || "M";
				let pProbs = {};

				if (pLabel && typeof pLabel === "object") {
					pProbs = pLabel.probabilities || {};
					pLabel = pLabel.prediction || "M";
				}

				setPrediction({
					prediction: pLabel,
					probabilities: pProbs,
					window_percent: 0,
					remaining_angle: data.regression?.remaining_angle,
				});
			} else if (data.prediction) {
				if (typeof data.prediction === "object" && data.prediction !== null) {
					setPrediction(data.prediction);
				} else {
					setPrediction(data);
				}
			}
		};

		socket.on("prediction", onPrediction);
		return () => {
			socket.off("prediction", onPrediction);
		};
	}, []);

	return <ScrewCore prediction={prediction} className={className} />;
};

export default ScrewSocket;
