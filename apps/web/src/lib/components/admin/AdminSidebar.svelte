<script lang="ts">
  import { page } from '$app/stores';

  interface NavItem {
    id: string;
    label: string;
    icon: string;
    href: string;
    badge?: string;
  }

  const navigation: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊', href: '/admin' },
    { id: 'orders', label: 'Заказы', icon: '📦', href: '/admin/orders' },
    { id: 'users', label: 'Пользователи', icon: '👥', href: '/admin/users' },
    { id: 'subscriptions', label: 'Подписки', icon: '⭐', href: '/admin/subscriptions' },
    { id: 'monitoring', label: 'Мониторинг', icon: '📈', href: '/admin/monitoring' },
    { id: 'system', label: 'Система', icon: '⚙️', href: '/admin/system' },
  ];

  $: currentPath = $page.url.pathname;
</script>

<div class="flex flex-col h-full bg-gray-900 text-white">
  <!-- Logo -->
  <div class="flex items-center px-6 py-4 border-b border-gray-700">
    <div class="w-8 h-8 bg-gradient-to-br from-pink-500 to-purple-600 rounded-lg flex items-center justify-center mr-3">
      <span class="text-white font-bold text-lg">Y</span>
    </div>
    <h1 class="text-lg font-semibold">Admin Panel</h1>
  </div>

  <!-- Navigation -->
  <nav class="flex-1 px-4 py-6 space-y-2">
    {#each navigation as item}
      <a
        href={item.href}
        class={`flex items-center px-4 py-3 text-sm rounded-lg transition-colors ${
          currentPath === item.href || (item.href === '/admin' && currentPath === '/admin')
            ? 'bg-pink-600 text-white'
            : 'text-gray-100 hover:bg-gray-800 hover:text-white'
        }`}
      >
        <span class="text-lg mr-3">{item.icon}</span>
        <span class="flex-1">{item.label}</span>
        {#if item.badge}
          <span class="ml-2 px-2 py-1 text-xs bg-red-500 text-white rounded-full">
            {item.badge}
          </span>
        {/if}
      </a>
    {/each}
  </nav>

  <!-- User Info -->
  <div class="border-t border-gray-700 px-6 py-4">
    <div class="text-sm text-gray-400">Администратор</div>
    <div class="text-white font-medium">Admin User</div>
  </div>
</div>

<style>
  /* Custom scrollbar for sidebar */
  nav {
    scrollbar-width: thin;
    scrollbar-color: #374151 #111827;
  }

  nav::-webkit-scrollbar {
    width: 6px;
  }

  nav::-webkit-scrollbar-track {
    background: #111827;
  }

  nav::-webkit-scrollbar-thumb {
    background: #374151;
    border-radius: 3px;
  }

  nav::-webkit-scrollbar-thumb:hover {
    background: #4b5563;
  }
</style>