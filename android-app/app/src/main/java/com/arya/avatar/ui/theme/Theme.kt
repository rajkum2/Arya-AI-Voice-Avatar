package com.arya.avatar.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val AryaDark = darkColorScheme(
    primary = Color(0xFF7C5CFF),
    secondary = Color(0xFF22D3EE),
    background = Color(0xFF070B14),
    surface = Color(0xFF141E33),
    onPrimary = Color.White,
    onBackground = Color(0xFFEEF2FF),
    onSurface = Color(0xFFEEF2FF),
    error = Color(0xFFF43F5E),
)

@Composable
fun AryaTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AryaDark,
        content = content,
    )
}
