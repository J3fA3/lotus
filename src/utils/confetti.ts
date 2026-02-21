import confetti from 'canvas-confetti';

export const triggerTaskCompletionConfetti = (taskId?: string) => {
    // Zen & Papyrus color palette: warm golds, earthy browns, muted greens, soft ambers
    const colors = ['#D4AF37', '#8B5A2B', '#A89F91', '#8F9779', '#D2B48C', '#DEB887'];

    let origin = { x: 0.5, y: 0.5 }; // Default to center

    if (taskId) {
        // Try to find the element (task card, or detail sheet header)
        const el = document.querySelector(`[data-task-id="${taskId}"]`);
        if (el) {
            const rect = el.getBoundingClientRect();
            origin = {
                x: (rect.left + rect.width / 2) / window.innerWidth,
                y: (rect.top + rect.height / 2) / window.innerHeight,
            };
        }
    }

    const count = 200;
    const defaults = {
        origin,
        colors: colors,
        zIndex: 10000, // Make sure it's on top of modals
        disableForReducedMotion: true
    };

    function fire(particleRatio: number, opts: confetti.Options) {
        confetti({
            ...defaults,
            ...opts,
            particleCount: Math.floor(count * particleRatio)
        });
    }

    // Realistic burst
    fire(0.25, {
        spread: 26,
        startVelocity: 55,
    });
    fire(0.2, {
        spread: 60,
    });
    fire(0.35, {
        spread: 100,
        decay: 0.91,
        scalar: 0.8
    });
    fire(0.1, {
        spread: 120,
        startVelocity: 25,
        decay: 0.92,
        scalar: 1.2
    });
    fire(0.1, {
        spread: 120,
        startVelocity: 45,
    });
};
