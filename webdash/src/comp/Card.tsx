import React, { ReactNode } from "react";

interface CardProps {
	children: ReactNode;
	title?: string;
}

const Card: React.FC<CardProps> = ({ children, title }) => {
	return (
		<div className="card">
			{title && (
				<div className="card-header">
					<h3 className="card-title">{title}</h3>
				</div>
			)}
			<div className="card-body">{children}</div>
		</div>
	);
};

export default Card;
