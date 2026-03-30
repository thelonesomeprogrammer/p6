import type React from "react";
import { useEffect, useState, useCallback } from "react";
import { socket } from "../socket";
import Card from "./Card";
import Select from "./Select";

interface PredictionResult {
    prediction: string;
    probabilities: Record<string, number>;
    window_percent: number;
    remaining_angle?: number;
}

const PredictorCard: React.FC<{ className?: string }> = ({ className = "" }) => {
    const [modelType, setModelType] = useState<string>("rf");
    const [predictions, setPredictions] = useState<PredictionResult[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const fetchPredictions = useCallback(async (signal?: AbortSignal) => {
        setIsLoading(true);
        setError(null);
        try {
            const res = await fetch(`http://localhost:5000/predict_all?model=${modelType}`, { signal });
            const data = await res.json();
            if (data.error) {
                setError(data.error);
                setPredictions([]);
            } else if (data.predictions) {
                setPredictions(data.predictions);
            }
        } catch (e: any) {
            if (e.name === "AbortError") return;
            setError("Failed to connect to backend");
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    }, [modelType]);

    useEffect(() => {
        const controller = new AbortController();

        const onRunFinished = () => {
            console.log("Run finished, auto-predicting...");
            fetchPredictions(controller.signal);
        };

        socket.on("runFinished", onRunFinished);

        return () => {
            socket.off("runFinished", onRunFinished);
            controller.abort();
        };
    }, [fetchPredictions]);

    return (
        <Card className={`flex flex-col ${className} min-w-[300px]`}>
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-semibold text-gray-700">
                    ML Predictor
                </h2>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase text-gray-400">Model</span>
                    <Select 
                        value={modelType} 
                        onChange={setModelType} 
                        options={["rf", "gb"]} 
                        className="w-16"
                    />
                </div>
            </div>

            <div className="flex-1 flex flex-col gap-2">
                <button 
                    onClick={fetchPredictions}
                    disabled={isLoading}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded text-sm font-semibold py-1 transition-colors"
                >
                    {isLoading ? "Predicting..." : "Run Prediction"}
                </button>

                {error && (
                    <div className="text-xs text-red-500 bg-red-50 p-2 rounded border border-red-100">
                        {error}
                    </div>
                )}

                <div className="flex-1 overflow-y-auto max-h-[200px] border rounded border-gray-100 bg-gray-50/50">
                    <table className="w-full text-left border-collapse">
                        <thead className="sticky top-0 bg-white border-b border-gray-200">
                            <tr>
                                <th className="p-2 text-[10px] font-bold text-gray-400 uppercase">Window</th>
                                <th className="p-2 text-[10px] font-bold text-gray-400 uppercase">Label</th>
                                <th className="p-2 text-[10px] font-bold text-gray-400 uppercase">Conf</th>
                                <th className="p-2 text-[10px] font-bold text-gray-400 uppercase">Remaining</th>
                            </tr>
                        </thead>
                        <tbody>
                            {predictions.map((p, i) => {
                                const conf = p.probabilities[p.prediction] || 0;
                                return (
                                    <tr key={i} className="border-b border-gray-50 hover:bg-white transition-colors">
                                        <td className="p-2 text-xs font-mono text-gray-500">{p.window_percent}%</td>
                                        <td className="p-2">
                                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                                                p.prediction === 'N' ? 'bg-green-100 text-green-700' :
                                                p.prediction === 'M' ? 'bg-blue-100 text-blue-700' :
                                                p.prediction === 'OT' ? 'bg-orange-100 text-orange-700' :
                                                'bg-red-100 text-red-700'
                                            }`}>
                                                {p.prediction}
                                            </span>
                                        </td>
                                        <td className="p-2 text-xs font-mono text-gray-600">
                                            {(conf * 100).toFixed(0)}%
                                        </td>
                                        <td className="p-2 text-xs font-mono text-gray-600">
                                            {p.remaining_angle ? `${p.remaining_angle.toFixed(1)}°` : "-"}
                                        </td>
                                    </tr>
                                );
                            })}
                            {predictions.length === 0 && !isLoading && !error && (
                                <tr>
                                    <td colSpan={4} className="p-4 text-center text-xs text-gray-400 italic">
                                        No data to predict
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </Card>
    );
};

export default PredictorCard;
