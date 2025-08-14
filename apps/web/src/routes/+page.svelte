<script lang="ts">
  import { onMount } from 'svelte';
  import Button from '$components/ui/Button.svelte';
  import KawaiiButton from '$components/ui/KawaiiButton.svelte';
  import KawaiiCard from '$components/ui/KawaiiCard.svelte';
  import FlowerDecoration from '$components/decorative/FlowerDecoration.svelte';
  import { configStore } from '$stores/config';
  import { fade, fly } from 'svelte/transition';

  $: config = $configStore.config;
  $: currentKurs = $configStore.kurs;

  let mounted = false;

  onMount(() => {
    mounted = true;
  });
</script>

<svelte:head>
  <title>YuYu Lolita Shopping - Заказы из Китая</title>
  <meta name="description" content="YuYu Lolita Shopping - заказы товаров из Китая с доставкой в Россию. Быстро, надежно, выгодно." />
</svelte:head>

<!-- Hero Section -->
<section class="relative overflow-hidden hero-section">
  
  <!-- Coffee background overlay -->
  <div class="absolute inset-0 bg-gradient-to-br from-coffee-50/80 to-coffee-100/60"></div>

  <div class="relative container-custom section-py">
    <div class="text-center max-w-4xl mx-auto">
      <!-- Main heading -->
      {#if mounted}
        <h1 
          class="text-4xl md:text-6xl font-bold text-gray-900 mb-6 hero-text-shadow"
          in:fly={{ y: 30, duration: 600, delay: 100 }}
        >
          <span class="text-original-phrase">🌸 Заказы из Китая 🌸</span>
          <span class="text-original-phrase block">стали проще</span>
        </h1>
      {:else}
        <h1 class="text-4xl md:text-6xl font-bold text-gray-900 mb-6 hero-text-shadow">
          <span class="text-original-phrase">🌸 Заказы из Китая 🌸</span>
          <span class="text-original-phrase block">стали проще</span>
        </h1>
      {/if}

      <!-- Subtitle -->
      {#if mounted}
        <p 
          class="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed"
          in:fly={{ y: 30, duration: 600, delay: 200 }}
        >
          Профессиональная помощь в заказе товаров с китайских площадок. 
          Прозрачные цены, быстрая доставка, полное сопровождение.
        </p>
      {:else}
        <p class="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed">
          Профессиональная помощь в заказе товаров с китайских площадок. 
          Прозрачные цены, быстрая доставка, полное сопровождение.
        </p>
      {/if}

      <!-- Currency rate -->
      {#if mounted}
        <div 
          class="inline-flex items-center bg-white/80 backdrop-blur-sm border border-primary-200 rounded-full px-6 py-3 mb-8"
          in:fly={{ y: 30, duration: 600, delay: 300 }}
        >
          <div class="w-2 h-2 bg-green-500 rounded-full mr-3 animate-pulse"></div>
          <span class="text-gray-700 font-medium">
            Актуальный курс: <span class="text-primary-600 font-bold">{currentKurs} ₽/¥</span>
          </span>
        </div>
      {:else}
        <div class="inline-flex items-center bg-white/80 backdrop-blur-sm border border-primary-200 rounded-full px-6 py-3 mb-8">
          <div class="w-2 h-2 bg-green-500 rounded-full mr-3 animate-pulse"></div>
          <span class="text-gray-700 font-medium">
            Актуальный курс: <span class="text-primary-600 font-bold">{currentKurs} ₽/¥</span>
          </span>
        </div>
      {/if}

      <!-- CTA Buttons -->
      {#if mounted}
        <div 
          class="flex flex-col sm:flex-row gap-4 justify-center items-center"
          in:fly={{ y: 30, duration: 600, delay: 400 }}
        >
          <KawaiiButton href="/create">
            ✨ Создать заказ ✨
          </KawaiiButton>
          
          <KawaiiButton href="/track" variant="white">
            🔍 Отследить заказ
          </KawaiiButton>
        </div>
      {:else}
        <div class="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <KawaiiButton href="/create">
            ✨ Создать заказ ✨
          </KawaiiButton>
          
          <KawaiiButton href="/track" variant="white">
            🔍 Отследить заказ
          </KawaiiButton>
        </div>
      {/if}
    </div>
  </div>
</section>

<!-- Features Section -->
<section class="section-py bg-white/80">
  <div class="container-custom">
    <div class="text-center mb-16">
      <h2 class="text-3xl md:text-4xl font-kawaii font-bold text-gray-900 mb-4">
        🌟 Почему выбирают нас 🌟
      </h2>
      <p class="text-xl text-gray-600 max-w-2xl mx-auto font-body">
        Мы делаем процесс заказа из Китая максимально простым и безопасным
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <!-- Feature 1 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 100 }}>
          <KawaiiCard variant="sky" className="text-center hover-lift">
            <div class="text-6xl mb-4">🛡️</div>
            <h3 class="text-xl font-kawaii font-bold text-gray-900 mb-4">Надежность</h3>
            <p class="text-gray-600 leading-relaxed">
              Работаем с проверенными поставщиками. Гарантируем получение заказа или возврат средств.
            </p>
          </KawaiiCard>
        </div>
      {:else}
        <KawaiiCard variant="sky" className="text-center hover-lift">
          <div class="text-6xl mb-4">🛡️</div>
          <h3 class="text-xl font-kawaii font-bold text-gray-900 mb-4">Надежность</h3>
          <p class="text-gray-600 leading-relaxed">
            Работаем с проверенными поставщиками. Гарантируем получение заказа или возврат средств.
          </p>
        </KawaiiCard>
      {/if}

      <!-- Feature 2 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 200 }}>
          <KawaiiCard variant="pink" className="text-center hover-lift">
            <div class="text-6xl mb-4">💰</div>
            <h3 class="text-xl font-kawaii font-bold text-gray-900 mb-4">Выгодные цены</h3>
            <p class="text-gray-600 leading-relaxed">
              Честная комиссия 10%, актуальный курс валют, никаких скрытых платежей.
            </p>
          </KawaiiCard>
        </div>
      {:else}
        <KawaiiCard variant="pink" className="text-center hover-lift">
          <div class="text-6xl mb-4">💰</div>
          <h3 class="text-xl font-kawaii font-bold text-gray-900 mb-4">Выгодные цены</h3>
          <p class="text-gray-600 leading-relaxed">
            Честная комиссия 10%, актуальный курс валют, никаких скрытых платежей.
          </p>
        </KawaiiCard>
      {/if}

      <!-- Feature 3 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 300 }}>
          <KawaiiCard variant="mint" className="text-center hover-lift">
            <div class="text-6xl mb-4">🚀</div>
            <h3 class="text-xl font-kawaii font-bold text-gray-900 mb-4">Быстрая доставка</h3>
            <p class="text-gray-600 leading-relaxed">
              Доставка от 2 недель. Отслеживание на каждом этапе от заказа до получения.
            </p>
          </KawaiiCard>
        </div>
      {:else}
        <KawaiiCard variant="mint" className="text-center hover-lift">
          <div class="text-6xl mb-4">🚀</div>
          <h3 class="text-xl font-kawaii font-bold text-gray-900 mb-4">Быстрая доставка</h3>
          <p class="text-gray-600 leading-relaxed">
            Доставка от 2 недель. Отслеживание на каждом этапе от заказа до получения.
          </p>
        </KawaiiCard>
      {/if}
    </div>
  </div>
</section>

<!-- How it works -->
<section class="section-py bg-gray-50/80">
  <div class="container-custom">
    <div class="text-center mb-16">
      <h2 class="text-3xl md:text-4xl font-kawaii font-bold text-gray-900 mb-4">
        ⭐ Как это работает ⭐
      </h2>
      <p class="text-xl text-gray-600 max-w-2xl mx-auto font-body">
        Простой процесс в 4 шага
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
      <!-- Step 1 -->
      <div class="text-center">
        <div class="w-12 h-12 bg-primary-500 text-white rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-lg">
          1
        </div>
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Создайте заказ</h3>
        <p class="text-gray-600 text-sm">
          Укажите ссылки на товары и контактную информацию
        </p>
      </div>

      <!-- Step 2 -->
      <div class="text-center">
        <div class="w-12 h-12 bg-primary-500 text-white rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-lg">
          2
        </div>
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Получите расчет</h3>
        <p class="text-gray-600 text-sm">
          Мы рассчитаем стоимость с учетом комиссии и доставки
        </p>
      </div>

      <!-- Step 3 -->
      <div class="text-center">
        <div class="w-12 h-12 bg-primary-500 text-white rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-lg">
          3
        </div>
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Произведите оплату</h3>
        <p class="text-gray-600 text-sm">
          Оплатите заказ удобным способом
        </p>
      </div>

      <!-- Step 4 -->
      <div class="text-center">
        <div class="w-12 h-12 bg-primary-500 text-white rounded-full flex items-center justify-center mx-auto mb-4 font-bold text-lg">
          4
        </div>
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Получите товар</h3>
        <p class="text-gray-600 text-sm">
          Отслеживайте доставку и получайте посылку
        </p>
      </div>
    </div>
  </div>
</section>

<!-- CTA Section -->
<section class="section-py relative overflow-hidden" style="background: linear-gradient(135deg, rgba(239, 176, 182, 0.8) 0%, rgba(230, 217, 245, 0.8) 100%);">
  
  <div class="container-custom text-center relative z-10">
    <h2 class="text-3xl md:text-4xl font-kawaii font-bold text-gray-800 mb-4">
      💖 Готовы сделать заказ? 💖
    </h2>
    <p class="text-xl text-gray-700 mb-8 max-w-2xl mx-auto font-body">
      Присоединяйтесь к тысячам довольных клиентов
    </p>
    
    <div class="flex flex-col sm:flex-row gap-4 justify-center items-center">
      <KawaiiButton href="/create" className="bg-white text-primary-600 hover:bg-gray-50">
        ✨ Создать заказ сейчас ✨
      </KawaiiButton>
      
      <KawaiiButton href="/stories" variant="white">
        📚 Истории клиентов
      </KawaiiButton>
    </div>
  </div>
</section>