import type React from "react";

interface SelectProps {
	value: string;
	onChange: (value: string) => void;
	options: string[];
	className?: string;
}

const Select: React.FC<SelectProps> = ({
	value,
	onChange,
	options,
	className,
}) => {
	return (
		<div className="select-container">
			<select
				value={value}
				onChange={(e) => onChange(e.target.value)}
				className={`border border-gray-300 rounded px-2 py-1 text-sm cursor-pointer bg-gray-50 outline-none transition-all ${className}`}
			>
				{options.map((option) => (
					<option key={option} value={option}>
						{option}
					</option>
				))}
			</select>
		</div>
	);
};

export default Select;
