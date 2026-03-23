import ColectorCard from "./comp/ColectorCard";
import KXMLPlotter from "./comp/KXMLPlotter";
import RobotPlotter from "./comp/RobotPlotter";
import RobotMonitor from "./comp/RobotMonitor";
import "./App.css";

const App = () => {
	return (
		<main className="gap-4 p-4">
			<div className="flex">
				<RobotMonitor />
				<ColectorCard />
			</div>
			<KXMLPlotter />
			<RobotPlotter />
		</main>
	);
};

export default App;
