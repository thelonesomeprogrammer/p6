import ColectorCard from "./comp/ColectorCard";
import PredictorCard from "./comp/PredictorCard";
import ScrewFetch from "./comp/ScrewFetch";
import ScrewSocket from "./comp/ScrewSocket";
import KXMLFetch from "./comp/KXMLFetch";
import KXMLSocket from "./comp/KXMLSocket";
import RobotPlotter from "./comp/RobotPlotter";
import RobotMonitor from "./comp/RobotMonitor";
import PredictionPlotter from "./comp/PredictionPlotter";
import ModelSelector from "./comp/ModelSelector";
import "./App.scss";
import { useEffect, useState } from "react";

const App = () => {
	let [apiVersion, setApiVersion] = useState<string>("initializing...");
	let [model, setModel] = useState<string>("rf");

	useEffect(() => {
		fetch("/api/version")
			.then((res) => res.json())
			.then((data) => setApiVersion(data.version))
			.catch((err) => console.error("Error fetching API version:", err));
	}, []);

	return (
		<main className="flex flex-col gap-4 p-4">
			{apiVersion.includes("collector") ? (
				collector()
			) : apiVersion.includes("socket") ? (
				socketMode(model, setModel)
			) : (
				<div className="text-center text-gray-500">
					<p className="text-lg font-semibold">Backend Not live</p>
					<p>API version "{apiVersion}" does not indicate a live backend.</p>
					<p>Please ensure the backend server is running and accessible.</p>
				</div>
			)}
		</main>
	);
};

const collector = () => {
	return (
		<>
			<div className="flex gap-4">
				<RobotMonitor className="" />
				<ColectorCard className="" />
				<PredictorCard className="" />
				<ScrewFetch className="" />
			</div>
			<KXMLFetch />
			<RobotPlotter />
		</>
	);
};

const socketMode = (model: string, setModel: (m: string) => void) => {
	return (
		<>
			<div className="flex justify-between items-center mb-2">
				<h1 className="text-xl font-bold text-gray-800">Socket Mode</h1>
				<ModelSelector model={model} setModel={setModel} />
			</div>
			<div className="flex gap-4">
				<RobotMonitor />
				<ScrewSocket />
				<PredictionPlotter />
			</div>
			<KXMLSocket />
		</>
	);
};

export default App;
