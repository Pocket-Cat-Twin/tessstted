<script lang="ts">
  import { onMount } from 'svelte';
  import Button from '$components/ui/Button.svelte';
  import GothicButton from '$components/ui/KawaiiButton.svelte';
  import GothicCard from '$components/ui/KawaiiCard.svelte';
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
  <title>LolitaFashion.su - Ты мечтаешь — мы исполняем</title>
  <meta name="description" content="LolitaFashion.su - премиальный сервис заказов из Китая в Россию. Лолита мода, аксессуары, косметика и многое другое." />
</svelte:head>

<!-- Hero Section -->
<section class="relative overflow-hidden section-gothic-primary pattern-overlay-7">
  
  <div class="relative container-custom section-py">
    <div class="text-center max-w-4xl mx-auto">
      <!-- Main heading -->
      {#if mounted}
        <h1 
          class="text-4xl md:text-6xl font-bold text-elegant mb-8 hero-gothic text-shadow-gothic"
          in:fly={{ y: 30, duration: 600, delay: 100 }}
        >
          <span class="text-gradient block">Ты мечтаешь — мы исполняем</span>
        </h1>
      {:else}
        <h1 class="text-4xl md:text-6xl font-bold text-elegant mb-8 hero-gothic text-shadow-gothic">
          <span class="text-gradient block">Ты мечтаешь — мы исполняем</span>
        </h1>
      {/if}

      <!-- Subtitle -->
      {#if mounted}
        <p 
          class="text-xl text-gothic-secondary mb-12 max-w-3xl mx-auto leading-relaxed"
          in:fly={{ y: 30, duration: 600, delay: 200 }}
        >
          LolitaFashion.su — ваш надёжный проводник в мир лолита моды и японских трендов. 
          Мы специализируемся на заказах одежды, аксессуаров, косметики и уникальных товаров 
          из Китая с полным сопровождением от выбора до получения.
        </p>
      {:else}
        <p class="text-xl text-gothic-secondary mb-12 max-w-3xl mx-auto leading-relaxed">
          LolitaFashion.su — ваш надёжный проводник в мир лолита моды и японских трендов. 
          Мы специализируемся на заказах одежды, аксессуаров, косметики и уникальных товаров 
          из Китая с полным сопровождением от выбора до получения.
        </p>
      {/if}

      <!-- Currency rate -->
      {#if mounted}
        <div 
          class="inline-flex items-center glass rounded-lg px-6 py-4 mb-12 hover-glow"
          in:fly={{ y: 30, duration: 600, delay: 300 }}
        >
          <div class="w-3 h-3 bg-gothic-accent rounded-full mr-4 animate-pulse"></div>
          <span class="text-gothic-white font-medium">
            Актуальный курс: <span class="text-gothic-accent font-bold">{currentKurs} ₽/¥</span>
          </span>
        </div>
      {:else}
        <div class="inline-flex items-center glass rounded-lg px-6 py-4 mb-12 hover-glow">
          <div class="w-3 h-3 bg-gothic-accent rounded-full mr-4 animate-pulse"></div>
          <span class="text-gothic-white font-medium">
            Актуальный курс: <span class="text-gothic-accent font-bold">{currentKurs} ₽/¥</span>
          </span>
        </div>
      {/if}

      <!-- CTA Buttons -->
      {#if mounted}
        <div 
          class="flex flex-col sm:flex-row gap-6 justify-center items-center"
          in:fly={{ y: 30, duration: 600, delay: 400 }}
        >
          <a href="/create" class="btn-gothic hover-lift">
            Создать заказ
          </a>
          
          <a href="/track" class="btn-white hover-lift">
            Отследить заказ
          </a>
        </div>
      {:else}
        <div class="flex flex-col sm:flex-row gap-6 justify-center items-center">
          <a href="/create" class="btn-gothic hover-lift">
            Создать заказ
          </a>
          
          <a href="/track" class="btn-white hover-lift">
            Отследить заказ
          </a>
        </div>
      {/if}
    </div>
  </div>
</section>

<!-- Features Section -->
<section class="section-py section-gothic-secondary">
  <div class="container-custom">
    <div class="text-center mb-20">
      <h2 class="text-3xl md:text-4xl font-elegant font-bold text-gothic-white mb-6 gothic-ornament">
        Почему выбирают нас
      </h2>
      <p class="text-xl text-gothic-secondary max-w-2xl mx-auto">
        Мы делаем заказы из Китая максимально простыми и безопасными
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
      <!-- Feature 1 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 100 }}>
          <div class="card-gothic p-6 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <div class="w-8 h-8 bg-gothic-accent rounded-full"></div>
            </div>
            <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Лолита мода</h3>
            <p class="text-gothic-secondary leading-relaxed text-sm">
              Специализируемся на authentic лолита брендах: Baby, Angelic Pretty, BTSSB и других
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <div class="w-8 h-8 bg-gothic-accent rounded-full"></div>
          </div>
          <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Лолита мода</h3>
          <p class="text-gothic-secondary leading-relaxed text-sm">
            Специализируемся на authentic лолита брендах: Baby, Angelic Pretty, BTSSB и других
          </p>
        </div>
      {/if}

      <!-- Feature 2 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 200 }}>
          <div class="card-gothic p-6 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <div class="w-8 h-8 border-2 border-gothic-accent rounded-full"></div>
            </div>
            <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Безопасность</h3>
            <p class="text-gothic-secondary leading-relaxed text-sm">
              Проверенные поставщики, гарантия доставки товара или полный возврат средств
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <div class="w-8 h-8 border-2 border-gothic-accent rounded-full"></div>
          </div>
          <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Безопасность</h3>
          <p class="text-gothic-secondary leading-relaxed text-sm">
            Проверенные поставщики, гарантия доставки товара или полный возврат средств
          </p>
        </div>
      {/if}

      <!-- Feature 3 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 300 }}>
          <div class="card-gothic p-6 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <div class="w-8 h-8 bg-gradient-to-br from-gothic-accent to-gothic-charcoal rounded-full"></div>
            </div>
            <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Выгодные цены</h3>
            <p class="text-gothic-secondary leading-relaxed text-sm">
              Честная комиссия 10%, актуальный курс валют, никаких скрытых платежей
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <div class="w-8 h-8 bg-gradient-to-br from-gothic-accent to-gothic-charcoal rounded-full"></div>
          </div>
          <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Выгодные цены</h3>
          <p class="text-gothic-secondary leading-relaxed text-sm">
            Честная комиссия 10%, актуальный курс валют, никаких скрытых платежей
          </p>
        </div>
      {/if}

      <!-- Feature 4 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 400 }}>
          <div class="card-gothic p-6 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <div class="w-8 h-8 bg-gradient-to-tr from-gothic-accent to-gothic-white rounded-full"></div>
            </div>
            <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Быстрая доставка</h3>
            <p class="text-gothic-secondary leading-relaxed text-sm">
              Доставка от 2 недель. Отслеживание на каждом этапе от заказа до получения
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <div class="w-8 h-8 bg-gradient-to-tr from-gothic-accent to-gothic-white rounded-full"></div>
          </div>
          <h3 class="text-lg font-elegant font-bold text-gothic-white mb-4">Быстрая доставка</h3>
          <p class="text-gothic-secondary leading-relaxed text-sm">
            Доставка от 2 недель. Отслеживание на каждом этапе от заказа до получения
          </p>
        </div>
      {/if}
    </div>
  </div>
</section>

<!-- How it works -->
<section class="section-py section-gothic-primary">
  <div class="container-custom">
    <div class="text-center mb-20">
      <h2 class="text-3xl md:text-4xl font-elegant font-bold text-gothic-white mb-6 gothic-ornament">
        Как это работает
      </h2>
      <p class="text-xl text-gothic-secondary max-w-2xl mx-auto">
        Простой процесс в 4 шага
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
      <!-- Step 1 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          1
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Создание заказа</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          Укажите ссылки на товары и контактную информацию
        </p>
      </div>

      <!-- Step 2 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          2
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Расчёт стоимости</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          Рассчитываем стоимость включая комиссию и доставку
        </p>
      </div>

      <!-- Step 3 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          3
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Оплата заказа</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          Оплачиваете заказ удобным для вас способом
        </p>
      </div>

      <!-- Step 4 -->
      <div class="text-center group">
        <div class="w-16 h-16 glass-intense rounded-full flex items-center justify-center mx-auto mb-6 font-bold text-xl text-gothic-white group-hover:scale-110 transition-transform duration-300">
          4
        </div>
        <h3 class="text-lg font-elegant font-semibold text-gothic-white mb-3">Получение товара</h3>
        <p class="text-gothic-secondary text-sm leading-relaxed">
          Отслеживаете доставку и получаете посылку
        </p>
      </div>
    </div>
  </div>
</section>

<!-- CTA Section -->
<section class="section-py relative overflow-hidden section-gothic-secondary pattern-overlay-7">
  
  <div class="container-custom text-center relative z-10">
    <h2 class="text-3xl md:text-4xl font-elegant font-bold text-gothic-white mb-6 gothic-ornament">
      Готовы сделать заказ?
    </h2>
    <p class="text-xl text-gothic-secondary mb-12 max-w-2xl mx-auto">
      Присоединяйтесь к тысячам довольных клиентов
    </p>
    
    <div class="flex flex-col sm:flex-row gap-6 justify-center items-center">
      <a href="/create" class="btn-gothic hover-lift shadow-gothic-glow">
        Создать заказ
      </a>
      
      <a href="/stories" class="btn-white hover-lift">
        История клиентов
      </a>
    </div>
  </div>
</section>