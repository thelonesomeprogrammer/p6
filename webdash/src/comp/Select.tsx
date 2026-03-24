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
				className={`border rounded px-2 py-1 text-sm bg-white cursor-pointer ${className}`}
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
