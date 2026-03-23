import type React from "react";
import type { ReactNode } from "react";

interface CardProps {
	children: ReactNode;
	className?: string;
}

const Card: React.FC<CardProps> = ({ children, className }) => {
	return (
		<div className={`card ${className || ""}`}>
			<div className="card-content w-full h-full">{children}</div>
		</div>
	);
};

export default Card;
