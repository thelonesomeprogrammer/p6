import type React from "react";

interface ExpandToggleButtonProps {
	isOpen: boolean;
	onClick: () => void;
}

const ExpandToggleButton: React.FC<ExpandToggleButtonProps> = ({
	isOpen,
	onClick,
}) => {
	// The lines will rotate around their own centers.
	// To keep them meeting at the vertex, we position their centers
	// offset from the middle by half of their horizontal projection.
	return (
		<button
			type="button"
			onClick={onClick}
			className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center hover:bg-gray-300 transition-colors focus:outline-none group"
			aria-label={isOpen ? "Collapse" : "Expand"}
		>
			<div className="relative w-5 h-5 flex items-center justify-center">
				{/* Left side of the arrow */}
				<div
					className={`absolute w-[10px] h-[2.5px] bg-gray-600 rounded-full transition-all duration-300 ${
						isOpen
							? "rotate-45 -translate-x-[3.2px]"
							: "-rotate-45 -translate-x-[3.2px]"
					}`}
					style={{ transformOrigin: "center" }}
				/>
				{/* Right side of the arrow */}
				<div
					className={`absolute w-[10px] h-[2.5px] bg-gray-600 rounded-full transition-all duration-300 ${
						isOpen
							? "-rotate-45 translate-x-[3.2px]"
							: "rotate-45 translate-x-[3.2px]"
					}`}
					style={{ transformOrigin: "center" }}
				/>
			</div>
		</button>
	);
};

export default ExpandToggleButton;
