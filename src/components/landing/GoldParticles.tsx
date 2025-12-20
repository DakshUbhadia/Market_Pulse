"use client";
import React, { useEffect, useState } from "react";
import Particles, { initParticlesEngine } from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";

const GoldParticles = () => {
  const [init, setInit] = useState(false);

  useEffect(() => {
    initParticlesEngine(async (engine) => {
      await loadSlim(engine);
    }).then(() => {
      setInit(true);
    });
  }, []);

  if (!init) return null;

  return (
    <Particles
      id="gold-particles"
      options={{
        fullScreen: {
          enable: true,
          zIndex: -1,
        },
        background: {
          color: {
            value: "#0a0a0a",
          },
        },
        particles: {
          number: {
            value: 80,
            density: {
              enable: true,
            },
          },
          color: {
            value: "#D4AF37",
          },
          shape: {
            type: "circle",
          },
          opacity: {
            value: { min: 0.1, max: 0.5 },
            animation: {
              enable: true,
              speed: 1,
              sync: false,
            },
          },
          size: {
            value: { min: 1, max: 4 },
          },
          links: {
            enable: false,
          },
          move: {
            enable: true,
            speed: 0.8,
            direction: "none",
            random: true,
            straight: false,
            outModes: {
              default: "out",
            },
          },
        },
        interactivity: {
          detectsOn: "canvas",
          events: {
            onHover: {
              enable: true,
              mode: "bubble",
            },
            onClick: {
              enable: true,
              mode: "push",
            },
          },
          modes: {
            bubble: {
              distance: 200,
              size: 6,
              duration: 2,
              opacity: 0.8,
            },
            push: {
              quantity: 4,
            },
          },
        },
        detectRetina: true,
      }}
    />
  );
};

export default GoldParticles;
