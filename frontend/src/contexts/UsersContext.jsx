import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import axios from "axios";

const UsersContext = createContext({
    users: [],
    loading: false,
    error: null,
    refreshUsers: () => {},
    addUser: () => {},
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

// ⭐ NEW: Add user to backend & refresh list
const addUser = useCallback(
  async (userData) => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();

      // Text fields – keys must match FastAPI params
      formData.append("name", userData.name);
	  const age = parseInt(userData.age, 10);
	  formData.append("age", String(Number.isNaN(age) ? 0 : age));
      formData.append("sex", userData.sex);
      formData.append("height", userData.height);
      formData.append("weight", userData.weight);
      formData.append("insurance", userData.insurance);
      formData.append("allergies", userData.allergies);
      formData.append("conditions", userData.conditions); 
	  // UsersContext.jsx (already there)
	if (userData.profile_pic) {
		formData.append("profile_pic", userData.profile_pic);
		}


      const res = await axios.post(
        "http://localhost:8000/add_user/",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      await fetchUsers();

      return res.data;
    } catch (err) {
      console.error(err);
      setError(err.message || "Failed to add user");
      throw err;
    } finally {
      setLoading(false);
    }
  },
  [fetchUsers]
);

    return (
        <UsersContext.Provider
            value={{
                users,
                loading,
                error,
                refreshUsers: fetchUsers,
                addUser, // ⭐ expose addUser
            }}
        >
            {children}
        </UsersContext.Provider>
    );
}

export function useUsers() {
    return useContext(UsersContext);
}

export default UsersContext;
