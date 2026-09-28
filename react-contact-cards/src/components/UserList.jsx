import UserCard from './UserCard.jsx';

// Parent list: turns the users array into one UserCard per user.
function UserList({ users, onRemoveUser }) {
  if (users.length === 0) {
    return <p className="empty">No contacts yet. Add one using the form.</p>;
  }

  return (
    <section className="user-list" aria-label="Contacts">
      {users.map((user) => (
        <UserCard
          key={user.id}
          name={user.name}
          email={user.email}
          phone={user.phone}
          onRemove={() => onRemoveUser(user.id)}
        />
      ))}
    </section>
  );
}

export default UserList;
