import ColectorCard from "./comp/ColectorCard";
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
			</div>
			<KXMLPlotter />
			<RobotPlotter />
		</main>
	);
};

export default App;
