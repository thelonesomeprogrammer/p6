import type React from "react";
import { useEffect, useState } from "react";
import { socket } from "../socket";
import { KXMLCore } from "./KXMLCore";

export const KXMLSocket: React.FC = () => {
	const [data, setData] = useState<any[]>([]);
	const [isOpen, setIsOpen] = useState<boolean>(true);

	useEffect(() => {
		const onKxmlData = (row: any) => {
			setData((prev) => [...prev, row]);
			console.log("ee")
			console.log(data)
		};

		const onRecordingStatus = (status: any) => {
			if (status.status === "started") {
				setData([]);
			}
		};

		socket.on("kxml_data", onKxmlData);
		socket.on("recording_status", onRecordingStatus);

		return () => {
			socket.off("kxml_data", onKxmlData);
			socket.off("recording_status", onRecordingStatus);
		};
	}, []);

	return (
		<KXMLCore
			data={data}
			isOpen={isOpen}
			setIsOpen={setIsOpen}
			isLoading={true}
		/>
	);
};

export default KXMLSocket;
