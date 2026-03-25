


function ToggleSwitch({ isOn, handleToggle }: { isOn: boolean; handleToggle: () => void }) {
	return (
		<div className="toggleswitch">
			<input
				type="checkbox"
				id="toggle-switch"
				checked={isOn}
				onChange={handleToggle}
			/>
			<label htmlFor="toggle-switch">Toggle</label>
		</div>
	);
}

export default ToggleSwitch;
