import React, { createContext, useCallback, useContext, useEffect, useState } from "react";

const UsersContext = createContext({
	users: [],
	refreshUsers: () => {},
});

export function UsersProvider({ children }) {
	const [users, setUsers] = useState([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState(null);

	const fetchUsers = useCallback(async () => {
		setLoading(true);
		setError(null);
		try {
			const res = await fetch("http://localhost:8000/users/");
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const data = await res.json();
			setUsers(data.users || []);
		} catch (err) {
			setError(err.message || "Failed to fetch users");
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchUsers();
	}, [fetchUsers]);

	return (
		<UsersContext.Provider value={{ users, loading, error, refreshUsers: fetchUsers }}>
			{children}
		</UsersContext.Provider>
	);
}

export function useUsers() {
	return useContext(UsersContext);
}

export default UsersContext;

