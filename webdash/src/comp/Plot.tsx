import type React from "react";
import {
	CartesianGrid,
	Legend,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

interface PlotProps {
	data: any[];
	xKey: string;
	yKeys: string[];
	colors?: string[];
	title?: string;
}

const Plot: React.FC<PlotProps> = ({ data, xKey, yKeys, colors, title }) => {
	const defaultColors = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#413ea0"];

	return (
		<div className="w-full mt-4">
			{title && (
				<h3 className="text-sm font-semibold text-gray-500 mb-2 uppercase">
					{title}
				</h3>
			)}
			<div className="h-64 w-full">
				<ResponsiveContainer width="100%" height="100%" minWidth={300} minHeight={250}>
				<LineChart
					data={data}
					margin={{
						top: 5,
						right: 30,
						left: 20,
						bottom: 5,
					}}
				>
					<CartesianGrid strokeDasharray="3 3" />
					<XAxis
						dataKey={xKey}
						type="number"
						domain={["dataMin", "dataMax"]}
						label={{ value: "Time (ms)", position: "insideBottomRight", offset: -10 }}
						tick={{ fontSize: 12 }}
					/>
					<YAxis tick={{ fontSize: 12 }} />
					<Tooltip />
					<Legend />
					{yKeys.map((key, index) => (
						<Line
							key={key}
							type="monotone"
							dataKey={key}
							stroke={
								colors
									? colors[index % colors.length]
									: defaultColors[index % defaultColors.length]
							}
							activeDot={{ r: 8 }}
							dot={false}
						/>
					))}
				</LineChart>
			</ResponsiveContainer>
			</div>
		</div>
	);
};

export default Plot;
