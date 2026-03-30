import type React from "react";
import { useEffect, useState, useCallback, useRef } from "react";
import { socket } from "../socket";
import Card from "./Card";

interface PredictionResult {
	prediction: string;
	probabilities: Record<string, number>;
	window_percent: number;
	remaining_angle?: number;
}

const ScrewCard: React.FC<{ className?: string }> = ({ className = "" }) => {
	const [prediction, setPrediction] = useState<PredictionResult | null>(null);
	const [isLoading, setIsLoading] = useState<boolean>(false);
	const [error, setError] = useState<string | null>(null);
    const [modelType] = useState<string>("rf"); // Default to rf like PredictorCard

	const fetchPrediction = useCallback(async (signal?: AbortSignal) => {
		setIsLoading(true);
		setError(null);
		try {
			const res = await fetch(`http://localhost:5000/predict_all?model=${modelType}`, { signal });
			const data = await res.json();
			if (data.error) {
				setError(data.error);
				setPrediction(null);
			} else if (data.predictions && data.predictions.length > 0) {
				// Get the 100% window prediction
				const lastPred = data.predictions[data.predictions.length - 1];
				setPrediction(lastPred);
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
	}, [modelType]);

	useEffect(() => {
		const controller = new AbortController();

		const onRunFinished = () => {
			fetchPrediction(controller.signal);
		};

		socket.on("runFinished", onRunFinished);

		return () => {
			socket.off("runFinished", onRunFinished);
			controller.abort();
		};
	}, [fetchPrediction]);

    // Initial fetch
    useEffect(() => {
        fetchPrediction();
    }, [fetchPrediction]);

    const remaining = prediction?.remaining_angle ?? 3100;
    // 3100 is 0% in, 0 is 100% in
    const percentIn = Math.max(0, Math.min(100, ((3100 - remaining) / 3100) * 100));
    
    // If final class is missing, we don't show the screw.
    // We check if prediction exists and has a label.
    const hasFinalClass = prediction && prediction.prediction;

	return (
		<Card className={`flex flex-col min-w-[300px] h-full ${className}`}>
			<div className="flex justify-between items-center mb-4">
				<h2 className="text-lg font-semibold text-gray-700">
					Screw Animation
				</h2>
                {isLoading && <span className="text-[10px] animate-pulse text-blue-500 font-bold uppercase">Updating...</span>}
			</div>

            <div className="flex-1 relative bg-gray-50 rounded-lg border border-gray-100 overflow-hidden min-h-[200px] flex flex-col items-center justify-center">
                {/* Wood block */}
                <div className="absolute top-1/2 w-full h-1/2 bg-[#8b4513] border-t-2 border-[#5d2e0d] shadow-[inset_0_4px_8px_rgba(0,0,0,0.2)]">
                    {/* Wood grain effect */}
                    <div className="absolute inset-0 opacity-10" 
                         style={{ backgroundImage: 'repeating-linear-gradient(90deg, transparent, transparent 30px, #000 30px, #000 31px), repeating-linear-gradient(0deg, transparent, transparent 20px, #000 20px, #000 21px)' }} />
                    
                    {/* Hole entry point */}
                    <div className="absolute top-0 left-1/2 -translate-x-1/2 w-10 h-2 bg-[#4a250b] rounded-full blur-[1px]" />
                </div>

                {/* Screw */}
                {hasFinalClass ? (
                    <div 
                        className="absolute left-1/2 w-8"
                        style={{ 
                            top: '50%', // Aligned with the wood surface
                            height: '120px',
                            // percentIn = 0 => translateY(-120px) => tip is at surface
                            // percentIn = 100 => translateY(-10px) => head is at surface
                            // Travel distance = 110px
                            transform: `translateX(-50%) translateY(${-120 + (percentIn * 1.1)}px)`,
                            transition: 'transform 2.5s cubic-bezier(0.45, 0.05, 0.55, 0.95)',
                            zIndex: 10
                        }}
                    >
                        {/* Screw Head (10px height) */}
                        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-12 h-3 bg-gradient-to-r from-gray-400 via-gray-100 to-gray-400 rounded-t-sm border border-gray-500 shadow-sm">
                            {/* Driver slot simulation */}
                            <div 
                                className="absolute top-1/2 left-1/2 -translate-y-1/2 h-2 bg-gray-600/40 rounded-full" 
                                style={{ 
                                    width: `${Math.abs(Math.cos(percentIn * 0.1)) * 10 + 2}px`,
                                    left: '50%',
                                    transform: 'translateX(-50%)'
                                }}
                            />
                        </div>

                        {/* Screw Neck (5px) */}
                        <div className="absolute top-[3px] left-1/2 -translate-x-1/2 w-5 h-2 bg-gray-400 border-x border-gray-500" />

                        {/* Screw Body (90px height) */}
                        <div className="absolute top-[5px] left-1/2 -translate-x-1/2 w-4 h-[100px] bg-gradient-to-r from-gray-400 via-gray-300 to-gray-400 border-x border-gray-500 overflow-hidden">
                             {/* Threads - Animating background position simulates rotation */}
                             <div className="absolute inset-0 opacity-40" 
                                  style={{ 
                                      backgroundImage: 'repeating-linear-gradient(-20deg, transparent, transparent 5px, #444 5px, #444 8px)',
                                      backgroundPosition: `0 ${percentIn * 3}px`,
                                      transition: 'background-position 2.5s cubic-bezier(0.45, 0.05, 0.55, 0.95)'
                                  }} />
                        </div>

                        {/* Screw Point (15px) */}
                        <div className="absolute top-[105px] left-1/2 -translate-x-1/2 w-0 h-0 border-l-[8px] border-l-transparent border-r-[8px] border-r-transparent border-t-[15px] border-t-gray-400" />
                    </div>
                ) : (
                    <div className="text-xs text-gray-400 italic font-medium uppercase tracking-wider">Awaiting classification</div>
                )}
                
                {error && (
                    <div className="absolute top-2 left-2 right-2 text-[10px] text-red-500 bg-white/80 p-1 rounded border border-red-100">
                        {error}
                    </div>
                )}
            </div>

            {hasFinalClass && (
                <div className="mt-3 flex items-center justify-between px-1">
                    <div className="flex flex-col">
                        <span className="text-[10px] font-bold text-gray-400 uppercase">Predicted State</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase w-fit ${
                            prediction.prediction === 'N' ? 'bg-green-100 text-green-700' :
                            prediction.prediction === 'M' ? 'bg-blue-100 text-blue-700' :
                            prediction.prediction === 'OT' ? 'bg-orange-100 text-orange-700' :
                            'bg-red-100 text-red-700'
                        }`}>
                            {prediction.prediction}
                        </span>
                    </div>
                    <div className="flex flex-col items-end">
                        <span className="text-[10px] font-bold text-gray-400 uppercase">Progress</span>
                        <span className="text-xs font-mono text-gray-600">{percentIn.toFixed(1)}%</span>
                    </div>
                </div>
            )}
		</Card>
	);
};

export default ScrewCard;
