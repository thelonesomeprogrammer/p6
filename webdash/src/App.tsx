import RobotMonitor from "./comp/RobotMonitor";
import ColectorCard from "./comp/ColectorCard";
import "./App.css";

const App = () => {
	return (
		<main className="flex">
			<RobotMonitor />
			<ColectorCard />
		</main>
	);
};

export default App;
