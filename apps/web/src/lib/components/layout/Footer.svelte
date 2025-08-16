<script lang="ts">
  import { configStore } from '$stores/config';

  $: config = $configStore.config;
  $: currentYear = new Date().getFullYear();
</script>

<footer class="section-gothic-primary pattern-overlay-7">
  <div class="container-custom">
    <!-- Main footer content -->
    <div class="py-16">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
        <!-- Company Info -->
        <div class="space-y-6">
          <div class="flex items-center space-x-3">
            <div class="w-10 h-10 glass-intense rounded-lg flex items-center justify-center border border-gothic-accent">
              <span class="text-gothic-white font-elegant text-lg">Y</span>
            </div>
            <span class="text-xl font-elegant text-gothic-white">YuYu Lolita</span>
          </div>
          <p class="text-gothic-secondary text-sm leading-relaxed">
            {config.site_description || 'Professional ordering service from China to Russia. Fast, reliable, efficient.'}
          </p>
        </div>

        <!-- Quick Links -->
        <div class="space-y-6">
          <h3 class="text-lg font-elegant text-gothic-white gothic-ornament">Quick Links</h3>
          <nav class="space-y-3">
            <a href="/" class="block text-gothic-secondary hover:text-gothic-accent transition-all duration-300 text-sm font-medium">
              Home
            </a>
            <a href="/create" class="block text-gothic-secondary hover:text-gothic-accent transition-all duration-300 text-sm font-medium">
              Create Order
            </a>
            <a href="/track" class="block text-gothic-secondary hover:text-gothic-accent transition-all duration-300 text-sm font-medium">
              Track Order
            </a>
            <a href="/stories" class="block text-gothic-secondary hover:text-gothic-accent transition-all duration-300 text-sm font-medium">
              Stories
            </a>
            <a href="/faq" class="block text-gothic-secondary hover:text-gothic-accent transition-all duration-300 text-sm font-medium">
              FAQ
            </a>
          </nav>
        </div>

        <!-- Support -->
        <div class="space-y-6">
          <h3 class="text-lg font-elegant text-gothic-white gothic-ornament">Support</h3>
          <div class="space-y-3">
            {#if config.contact_email}
              <a 
                href="mailto:{config.contact_email}" 
                class="flex items-center space-x-3 text-gothic-secondary hover:text-gothic-accent transition-all duration-300 text-sm font-medium group"
              >
                <div class="w-5 h-5 glass rounded-full flex items-center justify-center group-hover:border-gothic-accent border border-transparent transition-all duration-300">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <span>{config.contact_email}</span>
              </a>
            {/if}
            
            {#if config.contact_phone}
              <a 
                href="tel:{config.contact_phone}" 
                class="flex items-center space-x-3 text-gothic-secondary hover:text-gothic-accent transition-all duration-300 text-sm font-medium group"
              >
                <div class="w-5 h-5 glass rounded-full flex items-center justify-center group-hover:border-gothic-accent border border-transparent transition-all duration-300">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                </div>
                <span>{config.contact_phone}</span>
              </a>
            {/if}
          </div>
        </div>

        <!-- Social Media -->
        <div class="space-y-6">
          <h3 class="text-lg font-elegant text-gothic-white gothic-ornament">Connect With Us</h3>
          <div class="flex space-x-4">
            {#if config.telegram_link}
              <a 
                href={config.telegram_link} 
                target="_blank"
                rel="noopener noreferrer"
                class="w-12 h-12 glass-intense hover:border-gothic-accent border border-transparent rounded-lg flex items-center justify-center transition-all duration-300 hover-lift group"
                title="Telegram"
              >
                <svg class="w-5 h-5 text-gothic-secondary group-hover:text-gothic-accent transition-colors duration-300" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.13-.31-1.09-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
                </svg>
              </a>
            {/if}
            
            {#if config.vk_link}
              <a 
                href={config.vk_link} 
                target="_blank"
                rel="noopener noreferrer"
                class="w-12 h-12 glass-intense hover:border-gothic-accent border border-transparent rounded-lg flex items-center justify-center transition-all duration-300 hover-lift group"
                title="VK"
              >
                <svg class="w-5 h-5 text-gothic-secondary group-hover:text-gothic-accent transition-colors duration-300" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12.785 16.241s.288-.032.436-.194c.136-.148.131-.425.131-.425s-.019-1.299.582-1.491c.593-.189 1.354 1.256 2.161 1.81.612.419 1.078.327 1.078.327l2.164-.03s1.132-.071.595-.961c-.044-.073-.312-.658-1.608-1.859-1.357-1.257-1.175-1.053.459-3.224.995-1.32 1.393-2.126 1.268-2.472-.119-.329-.852-.242-.852-.242l-2.436.015s-.18-.025-.314.055c-.131.078-.215.26-.215.26s-.387 1.03-.902 1.906c-1.085 1.849-1.517 1.947-1.694 1.831-.41-.267-.308-1.073-.308-1.646 0-1.793.272-2.542-.53-2.732-.266-.063-.462-.105-1.142-.112-.873-.009-1.613.003-2.033.208-.28.136-.496.44-.364.458.163.022.533.1.729.368.253.346.244 1.122.244 1.122s.146 2.111-.34 2.373c-.334.18-.792-.187-1.775-1.856-.503-.859-.883-1.81-.883-1.81s-.073-.179-.203-.275c-.158-.117-.379-.154-.379-.154l-2.315.015s-.348.01-.475.161c-.113.134-.009.41-.009.41s1.816 4.25 3.873 6.396c1.885 1.969 4.025 1.84 4.025 1.84z"/>
                </svg>
              </a>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- Bottom footer -->
    <div class="border-t border-gothic-charcoal py-8">
      <div class="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
        <div class="text-gothic-secondary text-sm font-medium">
          © {currentYear} {config.site_name || 'YuYu Lolita Shopping'}. All rights reserved.
        </div>
        
        <div class="flex items-center space-x-8 text-sm">
          <a href="/privacy" class="text-gothic-secondary hover:text-gothic-accent transition-all duration-300 font-medium">
            Privacy Policy
          </a>
          <a href="/terms" class="text-gothic-secondary hover:text-gothic-accent transition-all duration-300 font-medium">
            Terms of Service
          </a>
        </div>
      </div>
    </div>
  </div>
</footer>