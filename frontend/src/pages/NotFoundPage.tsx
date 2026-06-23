import React from 'react';
import { NotFoundGlitch } from '../components/motion/not-found/glitch';

const NotFoundPage: React.FC = () => (
  <div className="min-h-screen flex items-center justify-center bg-background">
    <NotFoundGlitch
      homeHref="/"
      homeLabel="Back home"
      browseHref="/find"
      browseLabel="Find internships"
    />
  </div>
);

export default NotFoundPage;
