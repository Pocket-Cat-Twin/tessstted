<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { authStore } from '$stores/auth';
  import { configStore } from '$stores/config';
  import Button from '$components/ui/Button.svelte';

  export let showUserMenu = false;

  $: user = $authStore.user;
  $: config = $configStore.config;
  $: currentKurs = $configStore.kurs;

  // Theme switching logic
  let currentTheme = 'kawaii';

  function toggleTheme() {
    currentTheme = currentTheme === 'kawaii' ? 'coffee' : 'kawaii';
    applyTheme(currentTheme);
    localStorage.setItem('theme', currentTheme);
  }

  function applyTheme(theme: string) {
    if (theme === 'coffee') {
      document.documentElement.classList.add('theme-coffee');
    } else {
      document.documentElement.classList.remove('theme-coffee');
    }
  }

  // Initialize theme on component mount
  onMount(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'coffee') {
      currentTheme = 'coffee';
    }
    applyTheme(currentTheme);
  });

  function toggleUserMenu() {
    showUserMenu = !showUserMenu;
  }

  async function handleLogout() {
    await authStore.logout();
    showUserMenu = false;
  }
</script>

<header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-40">
  <nav class="container-custom">
    <div class="flex items-center justify-between h-16">
      <!-- Left side: Logo and navigation -->
      <div class="flex items-center space-x-8">
        <!-- Logo -->
        <a href="/" class="flex items-center space-x-2">
          <div class="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg flex items-center justify-center">
            <span class="text-white font-bold text-lg">Y</span>
          </div>
          <span class="text-xl font-bold text-gray-900 hidden sm:block">
            YuYu Lolita
          </span>
        </a>

        <!-- Navigation Links -->
        <div class="hidden md:flex items-center space-x-6">
          <a 
            href="/" 
            class="text-gray-600 hover:text-gray-900 transition-colors"
            class:text-primary-600={$page.url.pathname === '/'}
          >
            Главная
          </a>
          <a 
            href="/stories" 
            class="text-gray-600 hover:text-gray-900 transition-colors"
            class:text-primary-600={$page.url.pathname.startsWith('/stories')}
          >
            Истории
          </a>
          <a 
            href="/faq" 
            class="text-gray-600 hover:text-gray-900 transition-colors"
            class:text-primary-600={$page.url.pathname === '/faq'}
          >
            FAQ
          </a>
          <a 
            href="/track" 
            class="text-gray-600 hover:text-gray-900 transition-colors"
            class:text-primary-600={$page.url.pathname === '/track'}
          >
            Отследить заказ
          </a>
        </div>
      </div>

      <!-- Center: Currency rate -->
      <div class="hidden lg:flex items-center bg-gray-50 px-3 py-1.5 rounded-lg">
        <span class="text-sm text-gray-600">Курс:</span>
        <span class="text-sm font-semibold text-gray-900 ml-1">
          {currentKurs} ₽/¥
        </span>
      </div>

      <!-- Right side: Contact links and user menu -->
      <div class="flex items-center space-x-4">
        <!-- Theme Toggle Button -->
        <button
          type="button"
          on:click={toggleTheme}
          class="theme-switch-btn"
          title={currentTheme === 'kawaii' ? 'Переключить на кофейную тему' : 'Переключить на kawaii тему'}
        >
          {#if currentTheme === 'kawaii'}
            ☕
          {:else}
            🌸
          {/if}
        </button>

        <!-- Contact Links -->
        <div class="hidden sm:flex items-center space-x-3">
          {#if config.telegram_link}
            <a 
              href={config.telegram_link} 
              target="_blank"
              rel="noopener noreferrer"
              class="text-gray-500 hover:text-primary-600 transition-colors"
              title="Telegram"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.13-.31-1.09-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
              </svg>
            </a>
          {/if}
          
          {#if config.vk_link}
            <a 
              href={config.vk_link} 
              target="_blank"
              rel="noopener noreferrer"
              class="text-gray-500 hover:text-primary-600 transition-colors"
              title="VK"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12.785 16.241s.288-.032.436-.194c.136-.148.131-.425.131-.425s-.019-1.299.582-1.491c.593-.189 1.354 1.256 2.161 1.81.612.419 1.078.327 1.078.327l2.164-.03s1.132-.071.595-.961c-.044-.073-.312-.658-1.608-1.859-1.357-1.257-1.175-1.053.459-3.224.995-1.32 1.393-2.126 1.268-2.472-.119-.329-.852-.242-.852-.242l-2.436.015s-.18-.025-.314.055c-.131.078-.215.26-.215.26s-.387 1.03-.902 1.906c-1.085 1.849-1.517 1.947-1.694 1.831-.41-.267-.308-1.073-.308-1.646 0-1.793.272-2.542-.53-2.732-.266-.063-.462-.105-1.142-.112-.873-.009-1.613.003-2.033.208-.28.136-.496.44-.364.458.163.022.533.1.729.368.253.346.244 1.122.244 1.122s.146 2.111-.34 2.373c-.334.18-.792-.187-1.775-1.856-.503-.859-.883-1.81-.883-1.81s-.073-.179-.203-.275c-.158-.117-.379-.154-.379-.154l-2.315.015s-.348.01-.475.161c-.113.134-.009.41-.009.41s1.816 4.25 3.873 6.396c1.885 1.969 4.025 1.84 4.025 1.84z"/>
              </svg>
            </a>
          {/if}
        </div>

        <!-- User Menu -->
        {#if user}
          <div class="relative">
            <button
              type="button"
              on:click={toggleUserMenu}
              class="flex items-center space-x-2 text-gray-700 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md p-1"
            >
              <div class="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <span class="text-primary-700 font-medium text-sm">
                  {user.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <span class="hidden sm:block text-sm font-medium">{user.name}</span>
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {#if showUserMenu}
              <div class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-50">
                <a 
                  href="/profile" 
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  on:click={() => showUserMenu = false}
                >
                  Профиль
                </a>
                <a 
                  href="/orders" 
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                  on:click={() => showUserMenu = false}
                >
                  Мои заказы
                </a>
                {#if user.role === 'ADMIN'}
                  <hr class="my-1" />
                  <a 
                    href="/admin" 
                    class="block px-4 py-2 text-sm text-primary-600 hover:bg-primary-50"
                    on:click={() => showUserMenu = false}
                  >
                    Админ панель
                  </a>
                {/if}
                <hr class="my-1" />
                <button
                  type="button"
                  on:click={handleLogout}
                  class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
                >
                  Выйти
                </button>
              </div>
            {/if}
          </div>
        {:else}
          <div class="flex items-center space-x-3">
            <Button variant="ghost" href="/login" size="sm">
              Войти
            </Button>
            <Button variant="primary" href="/register" size="sm">
              Регистрация
            </Button>
          </div>
        {/if}

        <!-- Mobile menu button -->
        <button
          type="button"
          class="md:hidden p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
    </div>
  </nav>
</header>

<!-- Click outside to close user menu -->
{#if showUserMenu}
  <div 
    class="fixed inset-0 z-30" 
    role="button"
    tabindex="-1"
    on:click={() => showUserMenu = false}
    on:keydown={(e) => e.key === 'Escape' && (showUserMenu = false)}
  ></div>
{/if}