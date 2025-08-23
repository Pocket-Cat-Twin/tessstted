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
  let parallaxOffset = 0;

  function updateParallax() {
    const scrolled = window.pageYOffset;
    const windowHeight = window.innerHeight;
    
    // Находим футер и вычисляем его позицию
    const footer = document.querySelector('footer');
    
    if (footer) {
      const footerTop = footer.offsetTop;
      // Останавливаем паралакс за 200px до футера
      const stopPoint = footerTop - 200;
      
      // Если скролл достиг точки остановки, не обновляем паралакс
      if (scrolled >= stopPoint) {
        return; // Не изменяем parallaxOffset, оставляем последнее значение
      }
    }
    
    parallaxOffset = scrolled * 0.8;
    
    // Применяем CSS custom property для паралакс эффекта фоновых паттернов
    document.documentElement.style.setProperty('--pattern-parallax-offset', `${parallaxOffset}px`);
  }

  onMount(() => {
    mounted = true;
    
    // Добавляем обработчик скролла для паралакс эффекта
    window.addEventListener('scroll', updateParallax, { passive: true });
    
    // Инициализируем паралакс сразу
    updateParallax();
    
    return () => {
      window.removeEventListener('scroll', updateParallax);
    };
  });
</script>

<svelte:head>
  <title>LolitaFashion.su - Ты мечтаешь — мы исполняем</title>
  <meta name="description" content="LolitaFashion.su - премиальный сервис заказов из Китая в Россию. Лолита мода, аксессуары, косметика и многое другое." />
</svelte:head>


<!-- Hero Section -->
<section class="relative overflow-hidden py-16 md:py-24">
  
  <div class="relative container-custom">
    <div class="text-center max-w-4xl mx-auto hero-gothic-ornaments hero-text-background radial-gradient-background">
      <!-- Main heading -->
      {#if mounted}
        <h1 
          class="hero-title-size hero-title-above-all font-bold text-elegant mb-8 hero-gothic text-shadow-gothic"
          in:fly={{ y: 30, duration: 600, delay: 100 }}
        >
          <span class="text-gradient whitespace-nowrap">Ты мечтаешь — мы исполняем</span>
        </h1>
      {:else}
        <h1 class="hero-title-size hero-title-above-all font-bold text-elegant mb-8 hero-gothic text-shadow-gothic">
          <span class="text-gradient whitespace-nowrap">Ты мечтаешь — мы исполняем</span>
        </h1>
      {/if}

      <!-- Subtitle -->
      {#if mounted}
        <p 
          class="text-2xl md:text-3xl text-gothic-secondary mb-8 max-w-[70rem] mx-auto leading-relaxed"
          in:fly={{ y: 30, duration: 600, delay: 200 }}
        >
          LolitaFashion.su создан, чтобы каждая девушка, влюблённая в стиль лолита, могла легко и безопасно заказывать любимые вещи с китайских площадок. Прозрачные цены, полное сопровождение и забота о каждой детали — всё для того, чтобы вы наслаждались образом мечты.
        </p>
      {:else}
        <p class="text-2xl md:text-3xl text-gothic-secondary mb-8 max-w-[70rem] mx-auto leading-relaxed">
          LolitaFashion.su создан, чтобы каждая девушка, влюблённая в стиль лолита, могла легко и безопасно заказывать любимые вещи с китайских площадок. Прозрачные цены, полное сопровождение и забота о каждой детали — всё для того, чтобы вы наслаждались образом мечты.
        </p>
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
<section class="section-py">
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
              <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
            </div>
            <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Прозрачные цены</h3>
            <p class="text-gothic-secondary leading-relaxed text-lg">
              Честная комиссия, актуальный курс валют, никаких скрытых платежей.
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
          </div>
          <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Прозрачные цены</h3>
          <p class="text-gothic-secondary leading-relaxed text-lg">
            Честная комиссия, актуальный курс валют, никаких скрытых платежей.
          </p>
        </div>
      {/if}

      <!-- Feature 2 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 200 }}>
          <div class="card-gothic p-6 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
            </div>
            <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Надежность</h3>
            <p class="text-gothic-secondary leading-relaxed text-lg">
              Работаем с проверенными поставщиками. Гарантируем получение заказа или возврат средств.
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
          </div>
          <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Надежность</h3>
          <p class="text-gothic-secondary leading-relaxed text-lg">
            Работаем с проверенными поставщиками. Гарантируем получение заказа или возврат средств.
          </p>
        </div>
      {/if}

      <!-- Feature 3 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 300 }}>
          <div class="card-gothic p-6 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
            </div>
            <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Полное сопровождение</h3>
            <p class="text-gothic-secondary leading-relaxed text-lg">
              Мы на связи на всём пути заказа и всегда готовы помочь с любыми вопросами.
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
          </div>
          <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Полное сопровождение</h3>
          <p class="text-gothic-secondary leading-relaxed text-lg">
            Мы на связи на всём пути заказа и всегда готовы помочь с любыми вопросами.
          </p>
        </div>
      {/if}

      <!-- Feature 4 -->
      {#if mounted}
        <div in:fly={{ y: 30, duration: 600, delay: 400 }}>
          <div class="card-gothic p-6 text-center hover-lift hover-glow">
            <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
              <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
            </div>
            <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Доступ к китайским магазинам</h3>
            <p class="text-gothic-secondary leading-relaxed text-lg">
              Любимые платья, аксессуары и редкие находки становятся ближе — без языкового барьера и сложностей.
            </p>
          </div>
        </div>
      {:else}
        <div class="card-gothic p-6 text-center hover-lift hover-glow">
          <div class="w-16 h-16 mx-auto mb-6 glass-intense rounded-full flex items-center justify-center">
            <img src="/images/rose.png" alt="Rose icon" class="w-10 h-10 object-cover rounded-full opacity-80" />
          </div>
          <h3 class="text-2xl font-elegant font-bold text-gothic-white mb-4">Доступ к китайским магазинам</h3>
          <p class="text-gothic-secondary leading-relaxed text-lg">
            Любимые платья, аксессуары и редкие находки становятся ближе — без языкового барьера и сложностей.
          </p>
        </div>
      {/if}
    </div>
  </div>
</section>

<!-- How it works -->
<section class="section-py">
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
<section class="section-py relative overflow-hidden">
  
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