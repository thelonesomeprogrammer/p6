import ColectorCard from "./comp/ColectorCard";
import PredictorCard from "./comp/PredictorCard";
import ScrewCard from "./comp/ScrewCard";
import KXMLPlotter from "./comp/KXMLPlotter";
import RobotPlotter from "./comp/RobotPlotter";
import RobotMonitor from "./comp/RobotMonitor";
import "./App.scss";

const App = () => {
	return (
		<main className="flex flex-col gap-4 p-4">
			<div className="flex gap-4">
				<RobotMonitor className="" />
				<ColectorCard className="" />
				<PredictorCard className="" />
				<ScrewCard className="" />
			</div>
			<KXMLPlotter />
			<RobotPlotter />
		</main>
	);
};

export default App;
