import type React from "react";
import { useEffect, useState, useCallback } from "react";
import { socket } from "../socket";
import { KXMLCore } from "./KXMLCore";

export const KXMLFetch: React.FC = () => {
	const [data, setData] = useState<any[]>([]);
	const [isOpen, setIsOpen] = useState<boolean>(true);

	const fetchData = useCallback(async (signal?: AbortSignal) => {
		try {
			const response = await fetch("http://localhost:5000/kxml_data?points=500", {
				signal,
			});
			const raw = await response.json();
			setData(raw.kxml_data || []);
		} catch (error: any) {
			if (error.name === "AbortError") return;
			console.error("Error fetching KXML data:", error);
		}
	}, []);

	useEffect(() => {
		const controller = new AbortController();
		fetchData(controller.signal);

		const onRunFinished = () => {
			fetchData(controller.signal);
		};

		socket.on("runFinished", onRunFinished);

		return () => {
			socket.off("runFinished", onRunFinished);
			controller.abort();
		};
	}, [fetchData]);

	return <KXMLCore data={data} isOpen={isOpen} setIsOpen={setIsOpen} />;
};

export default KXMLFetch;
