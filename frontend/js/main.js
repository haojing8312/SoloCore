/**
 * SoloCore - Main JavaScript
 * Apple-style interactions and animations
 */

(function() {
    'use strict';

    // ============================================
    // Intersection Observer for Fade-in Animations
    // ============================================

    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                // Add stagger delay based on index
                setTimeout(() => {
                    entry.target.classList.add('visible');
                }, index * 100);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe all fade-in elements
    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach(el => observer.observe(el));

    // ============================================
    // Navbar Scroll Effect
    // ============================================

    const navbar = document.querySelector('.navbar');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        // Add shadow on scroll
        if (currentScroll > 50) {
            navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
        } else {
            navbar.style.boxShadow = 'none';
        }

        lastScroll = currentScroll;
    });

    // ============================================
    // 3D Parallax Effect (Mouse Movement)
    // ============================================

    const hero = document.querySelector('.hero');
    const heroContent = document.querySelector('.hero-content');

    if (hero && heroContent) {
        let mouseX = 0, mouseY = 0;
        let currentX = 0, currentY = 0;

        hero.addEventListener('mousemove', (e) => {
            const rect = hero.getBoundingClientRect();
            mouseX = (e.clientX - rect.left - rect.width / 2) / rect.width;
            mouseY = (e.clientY - rect.top - rect.height / 2) / rect.height;
        });

        // Smooth animation loop
        function animateParallax() {
            // Smooth interpolation
            currentX += (mouseX - currentX) * 0.1;
            currentY += (mouseY - currentY) * 0.1;

            // Apply transform
            if (heroContent) {
                const translateX = currentX * 20;
                const translateY = currentY * 20;
                heroContent.style.transform = `translate(${translateX}px, ${translateY}px)`;
            }

            // Apply parallax to gradient orbs
            const orbs = document.querySelectorAll('.gradient-orb');
            orbs.forEach((orb, index) => {
                const speed = (index + 1) * 10;
                const x = currentX * speed;
                const y = currentY * speed;
                orb.style.transform = `translate(${x}px, ${y}px)`;
            });

            requestAnimationFrame(animateParallax);
        }

        animateParallax();
    }

    // ============================================
    // 3D Card Tilt Effect
    // ============================================

    const cards = document.querySelectorAll('.hover-3d');

    cards.forEach(card => {
        card.addEventListener('mousemove', handleCardTilt);
        card.addEventListener('mouseleave', resetCardTilt);
    });

    function handleCardTilt(e) {
        const card = e.currentTarget;
        const rect = card.getBoundingClientRect();

        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = (y - centerY) / 10;
        const rotateY = (centerX - x) / 10;

        card.style.transform = `
            perspective(1000px)
            rotateX(${rotateX}deg)
            rotateY(${rotateY}deg)
            translateY(-10px)
            scale3d(1.02, 1.02, 1.02)
        `;
    }

    function resetCardTilt(e) {
        const card = e.currentTarget;
        card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateY(0) scale3d(1, 1, 1)';
    }

    // ============================================
    // Smooth Scroll for Anchor Links
    // ============================================

    const anchorLinks = document.querySelectorAll('a[href^="#"]');

    anchorLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href');

            // Skip if it's just "#"
            if (href === '#') return;

            e.preventDefault();

            const target = document.querySelector(href);
            if (target) {
                const navbarHeight = navbar.offsetHeight;
                const targetPosition = target.offsetTop - navbarHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // ============================================
    // Button Ripple Effect
    // ============================================

    const buttons = document.querySelectorAll('.btn');

    buttons.forEach(button => {
        button.addEventListener('click', createRipple);
    });

    function createRipple(e) {
        const button = e.currentTarget;
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();

        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = `${size}px`;
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;
        ripple.classList.add('ripple');

        button.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    }

    // Add ripple styles dynamically
    const style = document.createElement('style');
    style.textContent = `
        .btn {
            position: relative;
            overflow: hidden;
        }

        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.5);
            transform: scale(0);
            animation: ripple-animation 0.6s ease-out;
            pointer-events: none;
        }

        @keyframes ripple-animation {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);

    // ============================================
    // Progress Bar on Scroll
    // ============================================

    const progressBar = document.createElement('div');
    progressBar.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        height: 3px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        width: 0%;
        z-index: 9999;
        transition: width 0.1s ease-out;
    `;
    document.body.appendChild(progressBar);

    window.addEventListener('scroll', () => {
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight - windowHeight;
        const scrollTop = window.pageYOffset;
        const progress = (scrollTop / documentHeight) * 100;

        progressBar.style.width = `${progress}%`;
    });

    // ============================================
    // Scroll Indicator Hide on Scroll
    // ============================================

    const scrollIndicator = document.querySelector('.scroll-indicator');

    if (scrollIndicator) {
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 100) {
                scrollIndicator.style.opacity = '0';
                scrollIndicator.style.pointerEvents = 'none';
            } else {
                scrollIndicator.style.opacity = '1';
                scrollIndicator.style.pointerEvents = 'auto';
            }
        });
    }

    // ============================================
    // Performance: Reduce Motion for Users
    // ============================================

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    if (prefersReducedMotion.matches) {
        // Disable animations for users who prefer reduced motion
        document.documentElement.style.setProperty('--transition-fast', '0s');
        document.documentElement.style.setProperty('--transition-base', '0s');
        document.documentElement.style.setProperty('--transition-slow', '0s');
    }

    // ============================================
    // Initialize: Log Welcome Message
    // ============================================

    console.log(
        '%c✨ SoloCore - AI时代的超级个体操作系统',
        'font-size: 20px; font-weight: bold; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'
    );
    console.log(
        '%c🚀 欢迎来到 SoloCore! 让我们一起构建未来!',
        'font-size: 14px; color: #667eea;'
    );
    console.log(
        '%cGitHub: https://github.com/haojing8312/SoloCore',
        'font-size: 12px; color: #6E6E73;'
    );

    // ============================================
    // Easter Egg: Konami Code
    // ============================================

    let konamiCode = [];
    const konamiPattern = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];

    document.addEventListener('keydown', (e) => {
        konamiCode.push(e.key);
        konamiCode = konamiCode.slice(-konamiPattern.length);

        if (konamiCode.join(',') === konamiPattern.join(',')) {
            // Easter egg activated!
            document.body.style.animation = 'rainbow 2s linear infinite';

            const easterEggStyle = document.createElement('style');
            easterEggStyle.textContent = `
                @keyframes rainbow {
                    0% { filter: hue-rotate(0deg); }
                    100% { filter: hue-rotate(360deg); }
                }
            `;
            document.head.appendChild(easterEggStyle);

            setTimeout(() => {
                document.body.style.animation = '';
                easterEggStyle.remove();
            }, 5000);

            console.log('%c🎉 恭喜你发现了彩蛋！', 'font-size: 20px; color: #FF69B4;');
        }
    });

    // ============================================
    // Feature Card Click Analytics (Demo)
    // ============================================

    const featureCards = document.querySelectorAll('.feature-card');

    featureCards.forEach(card => {
        card.addEventListener('click', function() {
            const featureName = this.querySelector('.feature-title').textContent;
            console.log(`Feature card clicked: ${featureName}`);
            // In production, send to analytics
            // analytics.track('feature_card_click', { feature: featureName });
        });
    });

})();
