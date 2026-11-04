import Card from './components/Card.jsx';

function App() {
  return (
    <main className="app">
      <h1>Like / Unlike Cards</h1>
      <div className="cards">
        <Card title="JavaScript" />
        <Card title="React" />
        <Card title="Python" />
      </div>
    </main>
  );
}

export default App;
