import { useState } from 'react';

const emptyForm = { name: '', email: '', phone: '' };

// Controlled form. It owns only the text being typed; the finished user is
// handed to the parent through the onAddUser prop.
function UserForm({ onAddUser }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState('');

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    const name = form.name.trim();
    const email = form.email.trim();
    const phone = form.phone.trim();

    if (!name || !email || !phone) {
      setError('Please fill in all fields.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    onAddUser({ id: crypto.randomUUID(), name, email, phone });
    setForm(emptyForm);
    setError('');
  }

  return (
    <form className="user-form" onSubmit={handleSubmit} noValidate>
      <h2>Add a contact</h2>
      <label>
        Name
        <input name="name" value={form.name} onChange={handleChange} />
      </label>
      <label>
        Email
        <input name="email" type="email" value={form.email} onChange={handleChange} />
      </label>
      <label>
        Phone
        <input name="phone" type="tel" value={form.phone} onChange={handleChange} />
      </label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button type="submit">Add contact</button>
    </form>
  );
}

export default UserForm;
