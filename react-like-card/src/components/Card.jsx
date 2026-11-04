import { useState } from 'react';

// Each <Card /> gets its own copy of `liked`, so cards never affect each other.
function Card({ title }) {
  const [liked, setLiked] = useState(false);

  return (
    <div className="card">
      <h2>{title}</h2>
      <p className={liked ? 'label liked' : 'label'}>{liked ? 'Liked' : 'Not Liked'}</p>
      <button type="button" onClick={() => setLiked(!liked)}>
        {liked ? 'Unlike' : 'Like'}
      </button>
    </div>
  );
}

export default Card;
