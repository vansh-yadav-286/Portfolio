import { useState } from 'react';
import UserForm from './components/UserForm.jsx';
import UserList from './components/UserList.jsx';

function App() {
  // The single source of truth for all contacts lives here.
  const [users, setUsers] = useState([]);

  function addUser(user) {
    setUsers((current) => [...current, user]);
  }

  function removeUser(id) {
    setUsers((current) => current.filter((u) => u.id !== id));
  }

  return (
    <main className="app">
      <h1>Contact Cards</h1>
      <UserForm onAddUser={addUser} />
      <UserList users={users} onRemoveUser={removeUser} />
    </main>
  );
}

export default App;
