// One contact card. Purely presentational: everything comes from props.
function UserCard({ name, email, phone, onRemove }) {
  return (
    <article className="user-card">
      <h3>{name}</h3>
      <p><span>Email</span> {email}</p>
      <p><span>Phone</span> {phone}</p>
      <button type="button" className="remove-btn" onClick={onRemove}>Remove</button>
    </article>
  );
}

export default UserCard;
