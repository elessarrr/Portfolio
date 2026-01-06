// HTMX Configuration
document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // HTMX Error Handling
    document.body.addEventListener('htmx:responseError', function(evt) {
        alert('An error occurred while processing your request. Please try again.');
        console.error('HTMX Error:', evt.detail.error);
    });

    // Optional: Add loading class to body during requests if needed
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        // console.log('Request starting...');
    });
});
