// URL do grupo do WhatsApp
const whatsappGroupURL = 'https://chat.whatsapp.com/LSlj4MmAyMODcyW7us4vCY';

// Gerar QR Code
document.addEventListener('DOMContentLoaded', function() {
    // Configurar e gerar o QR Code
    const qrcodeContainer = document.getElementById('qrcode');
    
    if (qrcodeContainer) {
        const qrcode = new QRCode(qrcodeContainer, {
            text: whatsappGroupURL,
            width: 250,
            height: 250,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.H
        });
    }
    
    // Adicionar efeitos de hover nos cards
    addCardHoverEffects();
    
    // Tracking de cliques nos botões
    addClickTracking();
    
    // Adicionar partículas de confetti ocasionalmente
    addConfettiEffect();
    
    // Adicionar scroll suave
    addSmoothScroll();
});

// Efeitos de hover nos cards
function addCardHoverEffects() {
    const cards = document.querySelectorAll('.benefit-item, .oferta-card, .testimonial-card');
    
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'all 0.3s ease';
        });
    });
}

// Tracking de cliques
function addClickTracking() {
    const whatsappButtons = document.querySelectorAll('.btn-whatsapp, .btn-cta-final');
    const ofertasButton = document.querySelector('.btn-ofertas');
    const qrCode = document.querySelector('#qrcode');
    
    whatsappButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            console.log('Clique no botão WhatsApp');
            // Aqui você pode adicionar Google Analytics ou Facebook Pixel
            // gtag('event', 'click', {'event_category': 'WhatsApp', 'event_label': 'Entrar no Grupo'});
            
            // Adicionar animação de clique
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    });
    
    if (ofertasButton) {
        ofertasButton.addEventListener('click', function(e) {
            console.log('Clique no botão de Ofertas');
            // gtag('event', 'click', {'event_category': 'Ofertas', 'event_label': 'Ver Todas as Ofertas'});
            
            // Adicionar animação de clique
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
        });
    }
    
    if (qrCode) {
        qrCode.addEventListener('click', function() {
            console.log('Clique no QR Code');
            // Abrir o link do WhatsApp em dispositivos móveis
            if (isMobile()) {
                window.open(whatsappGroupURL, '_blank');
            }
        });
    }
}

// Verificar se é dispositivo móvel
function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

// Efeito de confetti ocasional
function addConfettiEffect() {
    // Criar partículas flutuantes
    const createFloatingEmoji = () => {
        const emojis = ['✨', '💝', '🎁', '⭐', '💎', '🌟', '💖'];
        const emoji = emojis[Math.floor(Math.random() * emojis.length)];
        
        const element = document.createElement('div');
        element.innerHTML = emoji;
        element.style.position = 'fixed';
        element.style.fontSize = '2rem';
        element.style.left = Math.random() * 100 + 'vw';
        element.style.top = '-50px';
        element.style.opacity = '0.7';
        element.style.pointerEvents = 'none';
        element.style.zIndex = '9999';
        element.style.animation = `floatDown ${3 + Math.random() * 3}s linear forwards`;
        
        document.body.appendChild(element);
        
        setTimeout(() => {
            element.remove();
        }, 6000);
    };
    
    // Adicionar keyframes para animação de queda
    const style = document.createElement('style');
    style.textContent = `
        @keyframes floatDown {
            to {
                transform: translateY(100vh) rotate(360deg);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    // Criar emojis flutuantes periodicamente
    setInterval(createFloatingEmoji, 3000);
}

// Scroll suave para links âncora
function addSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Adicionar animação de entrada quando elementos aparecem no viewport
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observar elementos para animação de entrada
document.addEventListener('DOMContentLoaded', function() {
    const animateElements = document.querySelectorAll('.benefit-item, .oferta-card, .testimonial-card');
    
    animateElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
});

// Contador de membros animado (opcional)
function animateCounter() {
    const counter = document.querySelector('.members-count');
    if (!counter) return;
    
    let count = 800;
    const target = 1000;
    const duration = 2000;
    const increment = (target - count) / (duration / 16);
    
    const timer = setInterval(() => {
        count += increment;
        if (count >= target) {
            count = target;
            clearInterval(timer);
        }
        // Atualizar o texto se necessário
    }, 16);
}

// Adicionar efeito de partículas no QR Code ao passar o mouse
const qrContainer = document.querySelector('.qr-container');
if (qrContainer) {
    qrContainer.addEventListener('mouseenter', function() {
        this.style.animation = 'none';
        setTimeout(() => {
            this.style.animation = '';
        }, 10);
    });
}

// Prevenir zoom em dispositivos iOS ao clicar nos botões
document.addEventListener('touchstart', function() {}, {passive: true});

// Log para depuração
console.log('🎉 FikbellaPromo - Landing Page carregada com sucesso!');
console.log('📱 Link do grupo:', whatsappGroupURL);

// Google Analytics / Facebook Pixel (descomentar quando configurar)
/*
// Google Analytics
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-XXXXXXXXXX'); // Substituir pelo seu ID

// Facebook Pixel
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', 'XXXXXXXXXX'); // Substituir pelo seu ID
fbq('track', 'PageView');
*/
