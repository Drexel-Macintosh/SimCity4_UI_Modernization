/*
 * This file is part of sc4-dll-utilities, a set of utilities for
 * SimCity 4 DLL Plugins.
 *
 * Copyright (C) 2026 Nicholas Hayes
 *
 * sc4-dll-utilities is free software: you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public License as
 * published by the Free Software Foundation, either version 2.1 of
 * the License, or (at your option) any later version.
 *
 * sc4-dll-utilities is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with sc4-dll-utilities.
 * If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once
#include <algorithm>
#include <cctype>
#include <charconv>
#include <string_view>
#include <vector>

namespace StringViewUtil
{
	/**
	 * @brief Compares two string view instances for equality while ignoring case.
	 * @param left The first string view to compare.
	 * @param right The second string view to compare.
	 * @return True if the string views are equal; otherwise, false.
	 */
	bool EqualsIgnoreCase(const std::string_view& left, const std::string_view& right);

	/**
	 * @brief Determines weather the input string view starts with the specified prefix while ignoring case.
	 * @param input The input string view.
	 * @param prefix The prefix to search for.
	 * @return True if the input string view starts with the specified prefix; otherwise, false.
	 */
	bool StartsWithIgnoreCase(const std::string_view& input, const std::string_view& prefix);

	/**
	 * @brief Splits the string view on the specified delimiter.
	 * @param input The input string view.
	 * @param delimiter The delimiter.
	 * @param results The split portions of the string view.
	 */
	void Split(
		const std::string_view& input,
		std::string_view::value_type delimiter,
		std::vector<std::string_view>& results);

	// The trim functions are based on public domain code from
	// https://gist.github.com/dk949/78dd944ea2b9763eb61cc5a652c35900

	/**
	 * @brief Trims characters from the start of the string view.
	 * @tparam T The trim predicate function.
	 * @param sv The input string view.
	 * @param pred The character trim predicate, defaults to white space.
	 * @return A trimmed copy of the string view.
	 */
	template <typename T = bool(*)(char)>
	constexpr std::string_view TrimStart(const std::string_view& sv, T pred = [](char v) { return !std::isspace(v); })
	{
		return { std::find_if(sv.begin(), sv.end(), pred), sv.end() };
	}

	/**
	 * @brief Trims characters from the end of the string view.
	 * @tparam T The trim predicate function.
	 * @param sv The input string view.
	 * @param pred The character trim predicate, defaults to white space.
	 * @return A trimmed copy of the string view.
	 */
	template<typename T = bool (*)(char)>
	constexpr std::string_view TrimEnd(const std::string_view& sv, T pred = [](char a) { return !std::isspace(a); })
	{
		return { sv.begin(), std::find_if(sv.rbegin(), sv.rend(), pred).base() };
	}

	/**
	 * @brief Trims characters from the start and end of the string view.
	 * @tparam T The trim predicate function.
	 * @param sv The input string view.
	 * @param pred The character trim predicate, defaults to white space.
	 * @return A trimmed copy of the string view.
	 */
	template<typename T = bool (*)(char)>
	constexpr std::string_view Trim(const std::string_view& sv, T pred = [](char a) { return !std::isspace(a); })
	{
		return TrimStart(TrimEnd(sv, pred), pred);
	}

	/**
	 * @brief Attempts to parse the specified string view as an arithmetic type.
	 * @tparam T The value type, must be bool, integer, or floating point.
	 * @tparam
	 * @param input The input string view.
	 * @param outValue The output value.
	 * @return True if the string view was successfully parsed; otherwise, false.
	 */
	template <typename T, typename = std::enable_if_t<std::is_arithmetic_v<T>>>
	bool TryParse(const std::string_view& input, T& outValue)
	{
		if constexpr (std::is_same_v<T, bool>)
		{
			if (input.length() == 1)
			{
				if (input[0] == '1')
				{
					outValue = true;
					return true;
				}
				else if (input[0] == '0')
				{
					outValue = false;
					return true;
				}
			}
			else if (
				EqualsIgnoreCase(input, "true") ||
				EqualsIgnoreCase(input, "on") ||
				EqualsIgnoreCase(input, "enabled"))
			{
				outValue = true;
				return true;
			}
			else if (
				EqualsIgnoreCase(input, "false") ||
				EqualsIgnoreCase(input, "off") ||
				EqualsIgnoreCase(input, "disabled"))
			{
				outValue = false;
				return true;
			}

			outValue = false;
			return false;
		}
		else if constexpr (
			std::is_same_v<T, int8_t> ||
			std::is_same_v<T, uint8_t> ||
			std::is_same_v<T, int16_t> ||
			std::is_same_v<T, uint16_t> ||
			std::is_same_v<T, int32_t> ||
			std::is_same_v<T, uint32_t> ||
			std::is_same_v<T, int64_t> ||
			std::is_same_v<T, uint64_t>)
		{
			const char* start = input.data();
			const char* end = start + input.size();

			int base = 10;

			if (StartsWithIgnoreCase(input, "0x"))
			{
				// std::from_chars can't parse hexadecimal numbers with the 0x prefix.
				start += 2;
				base = 16;
			}

			const std::from_chars_result result = std::from_chars(start, end, outValue, base);

			if (result.ec == std::errc{} && result.ptr == end)
			{
				return true;
			}

			outValue = 0;
			return false;
		}
		else if constexpr (
			std::is_same_v<T, float> ||
			std::is_same_v<T, double>)
		{
			const char* start = input.data();
			const char* end = start + input.size();

			const std::from_chars_result result = std::from_chars(start, end, outValue);

			if (result.ec == std::errc{} && result.ptr == end)
			{
				return true;
			}

			outValue = 0;
			return false;
		}
		else
		{
			static_assert(false, "T is an unsupported type.");
		}
	}
}
