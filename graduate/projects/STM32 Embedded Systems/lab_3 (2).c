/* Includes ------------------------------------------------------------------*/
#include <Lab_3.h>      // Project-specific header (placeholder)
#include <stdbool.h>    // For 'bool' type
#include <string.h>     // For string functions (e.g., strlen)
#include <stdio.h>      // For sprintf (data formatting)

/* Private variables ---------------------------------------------------------*/
// Hardware Abstraction Layer (HAL) Handles
TIM_HandleTypeDef my_tim6_handle;
TIM_HandleTypeDef my_tim7_handle;
UART_HandleTypeDef huart1;

// Input/Output Control Variables
static volatile bool ignoringInputs = false; // Debounce flag
static uint8_t rx_char;                     // Stores the received UART character

/* Stopwatch state variables -------------------------------------------------*/
typedef enum { STOPWATCH_PAUSED, STOPWATCH_RUNNING } StopwatchState;
static volatile StopwatchState stopwatchState = STOPWATCH_PAUSED;
static volatile uint32_t hundredths = 0;   // Main counter (0.01s increments)
static volatile bool timerOverflow = false; // Flag for 5-minute limit

/* Function prototypes -------------------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void Configure_Timer6(void);
static void Configure_Timer7(void);
static void MX_USART1_UART_Init(void);

/* ---------------------------------------------------------------------------*/
/* External Interrupt Callbacks */
/* ---------------------------------------------------------------------------*/
void EXTI0_IRQHandler(void) {
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0); // Handles PA0 (Start/Pause) interrupt
}

void EXTI9_5_IRQHandler(void) {
    HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_6); // Handles PC6 (Sample Time) interrupt
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin) {

    if (GPIO_Pin == GPIO_PIN_0) {  // PA0: Start/Pause Toggle
        if (stopwatchState == STOPWATCH_RUNNING) {
            stopwatchState = STOPWATCH_PAUSED;
            HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_RESET); // LD3 OFF
            HAL_UART_Transmit(&huart1, (uint8_t*)"Paused\r\n", 8, HAL_MAX_DELAY);
        } else {
            stopwatchState = STOPWATCH_RUNNING;
            HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_SET);  // LD3 ON
            HAL_UART_Transmit(&huart1, (uint8_t*)"Running\r\n", 9, HAL_MAX_DELAY);
        }
    }

    else if (GPIO_Pin == GPIO_PIN_6) {  // PC6: Sample Elapsed Time
        if (ignoringInputs) return; // Ignore input if debounce timer is running

        HAL_GPIO_WritePin(LD6_GPIO_Port, LD6_Pin, GPIO_PIN_SET);  // Turn on debounce LED (LD6)
        HAL_TIM_Base_Start_IT(&my_tim7_handle);                  // Start 1s debounce timer (TIM7)
        ignoringInputs = true;                                  // Set flag

        char msg[32];
        sprintf(msg, "%lu\r\n", hundredths);                    // Format hundredths count
        HAL_UART_Transmit(&huart1, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);
    }
}

/* ---------------------------------------------------------------------------*/
/* Timer Interrupt Handlers */
/* ---------------------------------------------------------------------------*/
void TIM6_DAC_IRQHandler(void) {
    HAL_TIM_IRQHandler(&my_tim6_handle); // Forward to HAL period elapsed callback
}

void TIM7_IRQHandler(void) {
    HAL_TIM_IRQHandler(&my_tim7_handle); // Forward to HAL period elapsed callback
}

void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {

    if (htim->Instance == TIM6) {
        // TIM6: Stopwatch time base (0.01s tick)
        if (stopwatchState == STOPWATCH_RUNNING) {
            hundredths++;
            if (hundredths >= 30000) { // Check for 5-minute overflow (30000 * 0.01s)
                stopwatchState = STOPWATCH_PAUSED;
                HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_RESET);
                HAL_UART_Transmit(&huart1, (uint8_t*)"Time elapsed\r\n", 14, HAL_MAX_DELAY);
                timerOverflow = true;
            }
        }
        HAL_GPIO_TogglePin(LD7_GPIO_Port, LD7_Pin); // Heartbeat LED toggle
    }

    else if (htim->Instance == TIM7) {
        // TIM7: Debounce timer expiry (1 second)
        HAL_TIM_Base_Stop_IT(&my_tim7_handle);       // Stop the timer
        HAL_GPIO_WritePin(LD6_GPIO_Port, LD6_Pin, GPIO_PIN_RESET); // Turn off debounce LED
        ignoringInputs = false;                     // Re-enable input processing
    }
}

/* ---------------------------------------------------------------------------*/
/* UART Handlers */
/* ---------------------------------------------------------------------------*/
void USART1_IRQHandler(void) {
    HAL_UART_IRQHandler(&huart1); // Forward to HAL receive complete callback
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *UartHandle) {

    if (UartHandle->Instance == USART1) {

        if (rx_char == 's') { // 's': Start/Pause toggle
            if (stopwatchState == STOPWATCH_RUNNING) {
                stopwatchState = STOPWATCH_PAUSED;
                HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_RESET);
                HAL_UART_Transmit(&huart1, (uint8_t*)"Paused\r\n", 8, HAL_MAX_DELAY);
            } else {
                stopwatchState = STOPWATCH_RUNNING;
                HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_SET);
                HAL_UART_Transmit(&huart1, (uint8_t*)"Running\r\n", 9, HAL_MAX_DELAY);
            }
        }

        else if (rx_char == 'f') { // 'f': Reset stopwatch
            hundredths = 0;
            stopwatchState = STOPWATCH_PAUSED;
            HAL_GPIO_WritePin(LD3_GPIO_Port, LD3_Pin, GPIO_PIN_RESET);
            HAL_UART_Transmit(&huart1, (uint8_t*)"Reset\r\n", 7, HAL_MAX_DELAY);
        }

        else if (rx_char == 'p') { // 'p': Sample elapsed time
            char msg[32];
            sprintf(msg, "%lu\r\n", hundredths);
            HAL_UART_Transmit(&huart1, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);
        }

        else { // Unrecognized command: Echo and error indicator
            HAL_UART_Transmit(&huart1, &rx_char, 1, HAL_MAX_DELAY);
            HAL_UART_Transmit(&huart1, (uint8_t*)"?\r\n", 3, HAL_MAX_DELAY);
        }

        HAL_UART_Receive_IT(&huart1, &rx_char, 1); // Re-enable interrupt for next byte
    }
}

/* ---------------------------------------------------------------------------*/
/* Core Initialization and Setup */
/* ---------------------------------------------------------------------------*/
void HAL_UART_MspInit(UART_HandleTypeDef* huart) {
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    if (huart->Instance == USART1) {
        // 1. Enable Clocks for USART1 and GPIOC
        __HAL_RCC_USART1_CLK_ENABLE();
        __HAL_RCC_GPIOC_CLK_ENABLE();
       
        // 2. Configure USART1 Pins (PC4=TX, PC5=RX)
        GPIO_InitStruct.Pin = GPIO_PIN_4 | GPIO_PIN_5;
        GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;          // Alternate Function Push-Pull
        GPIO_InitStruct.Pull = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
        GPIO_InitStruct.Alternate = GPIO_AF7_USART1;     // AF7 is mapped to USART1
        HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
    }
}

/* ---------------------------------------------------------------------------*/
int main(void) {

    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    HAL_GPIO_WritePin(LD6_GPIO_Port, LD6_Pin, GPIO_PIN_RESET); // Debounce LED off at start

    Configure_Timer6();
    HAL_TIM_Base_Start_IT(&my_tim6_handle);  // Start 0.01s base clock (TIM6)

    Configure_Timer7();
    MX_USART1_UART_Init();

    HAL_UART_Receive_IT(&huart1, &rx_char, 1); // Start continuous UART reception

    while (1) {
        // All stopwatch logic is handled by interrupts (FSM)
    }
}

/* ---------------------------------------------------------------------------*/
/* Peripheral Configurations */
/* ---------------------------------------------------------------------------*/
void SystemClock_Config(void) {
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    // Configure HSI as clock source and PLL settings
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
    RCC_OscInitStruct.HSIState = RCC_HSI_ON;
    RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSI;
    RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL16;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) Error_Handler();

    // Select PLL as system clock source (64MHz)
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
        RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
        Error_Handler();
}

static void MX_GPIO_Init(void) {
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    // Enable required GPIO clocks
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();

    // Initialize all User/State LEDs to OFF
    HAL_GPIO_WritePin(GPIOE,
        LD4_Pin | LD3_Pin | LD5_Pin | LD7_Pin |
        LD9_Pin | LD10_Pin | LD8_Pin | LD6_Pin,
        GPIO_PIN_RESET);

    // PA0: Start/Pause Button (Rising Edge Interrupt)
    GPIO_InitStruct.Pin = GPIO_PIN_0;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_RISING;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    // PC6: Sample Time Button (Falling Edge Interrupt)
    GPIO_InitStruct.Pin = GPIO_PIN_6;
    GPIO_InitStruct.Mode = GPIO_MODE_IT_FALLING;
    GPIO_InitStruct.Pull = GPIO_PULLUP;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    // Configure all LEDs as Output Push-Pull
    GPIO_InitStruct.Pin = LD4_Pin | LD3_Pin | LD5_Pin | LD7_Pin |
        LD9_Pin | LD10_Pin | LD8_Pin | LD6_Pin;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    // Enable and configure NVIC for PA0 (EXTI0)
    __HAL_GPIO_EXTI_CLEAR_FLAG(GPIO_PIN_0);
    HAL_NVIC_ClearPendingIRQ(EXTI0_IRQn);
    HAL_NVIC_SetPriority(EXTI0_IRQn, 1, 0);
    HAL_NVIC_EnableIRQ(EXTI0_IRQn);

    // Enable and configure NVIC for PC6 (EXTI9_5)
    __HAL_GPIO_EXTI_CLEAR_FLAG(GPIO_PIN_6);
    HAL_NVIC_ClearPendingIRQ(EXTI9_5_IRQn);
    HAL_NVIC_SetPriority(EXTI9_5_IRQn, 3, 0);
    HAL_NVIC_EnableIRQ(EXTI9_5_IRQn);
}

void Configure_Timer6(void) {
    __HAL_RCC_TIM6_CLK_ENABLE();
    my_tim6_handle.Instance = TIM6;
    // Prescaler: (64MHz / 64000) = 1kHz
    my_tim6_handle.Init.Prescaler = 64000 - 1;
    // Period: (1kHz / 10) = 100Hz = 0.01s (Stopwatch Base)
    my_tim6_handle.Init.Period = 10 - 1;
    HAL_NVIC_SetPriority(TIM6_DAC_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(TIM6_DAC_IRQn);
    HAL_TIM_Base_Init(&my_tim6_handle);
    __HAL_TIM_CLEAR_IT(&my_tim6_handle, TIM_IT_UPDATE);
    __HAL_TIM_SET_COUNTER(&my_tim6_handle, 0);
}

void Configure_Timer7(void) {
    __HAL_RCC_TIM7_CLK_ENABLE();
    my_tim7_handle.Instance = TIM7;
    my_tim7_handle.Init.CounterMode = TIM_COUNTERMODE_UP;
    // Prescaler: (64MHz / 4000) = 16kHz
    my_tim7_handle.Init.Prescaler = 4000 - 1;
    // Period: (16kHz / 16000) = 1Hz = 1s (Debounce Period)
    my_tim7_handle.Init.Period = 16000 - 1;
    HAL_NVIC_SetPriority(TIM7_IRQn, 2, 1);
    HAL_NVIC_EnableIRQ(TIM7_IRQn);
    HAL_TIM_Base_Init(&my_tim7_handle);
    __HAL_TIM_CLEAR_IT(&my_tim7_handle, TIM_IT_UPDATE);
    __HAL_TIM_SET_COUNTER(&my_tim7_handle, 0);
}

static void MX_USART1_UART_Init(void) {
    huart1.Instance = USART1;
    huart1.Init.BaudRate = 115200; // Target Baud Rate
    huart1.Init.WordLength = UART_WORDLENGTH_8B;
    huart1.Init.StopBits = UART_STOPBITS_1;
    huart1.Init.Parity = UART_PARITY_NONE;
    huart1.Init.Mode = UART_MODE_TX_RX;
    huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
    huart1.Init.OverSampling = UART_OVERSAMPLING_16;
    huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
    if (HAL_UART_Init(&huart1) != HAL_OK) Error_Handler();

    HAL_NVIC_SetPriority(USART1_IRQn, 0, 0);
    HAL_NVIC_EnableIRQ(USART1_IRQn);
}

void Error_Handler(void) {
    __disable_irq(); // Lock system on error
    while (1) {}
}
