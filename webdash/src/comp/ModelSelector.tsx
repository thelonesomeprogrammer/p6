import type React from "react";
import Select from "./Select";

interface ModelSelectorProps {
	model: string;
	setModel: (model: string) => void;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ model, setModel }) => {
	return (
		<div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-lg border border-gray-200 shadow-sm">
			<span className="text-[10px] font-bold uppercase text-gray-400">
				Active Model
			</span>
			<Select
				value={model}
				onChange={setModel}
				options={["rf", "gb", "lstm"]}
				className="w-20"
			/>
		</div>
	);
};

export default ModelSelector;
