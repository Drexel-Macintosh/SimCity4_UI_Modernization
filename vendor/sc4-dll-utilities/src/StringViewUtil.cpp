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

#include "StringViewUtil.h"

namespace
{
	bool CaseInsensitiveComparer(char a, char b)
	{
		return std::toupper(static_cast<unsigned char>(a)) == std::toupper(static_cast<unsigned char>(b));
	}
}

bool StringViewUtil::EqualsIgnoreCase(const std::string_view& left, const std::string_view& right)
{
	return left.length() == right.length()
		&& std::equal(left.begin(), left.end(), right.begin(), right.end(), CaseInsensitiveComparer);
}

bool StringViewUtil::StartsWithIgnoreCase(const std::string_view& input, const std::string_view& prefix)
{
	return input.length() >= prefix.length()
		&& std::equal(prefix.begin(), prefix.end(), input.begin(), CaseInsensitiveComparer);
}

void StringViewUtil::Split(
	const std::string_view& input,
	std::string_view::value_type delimiter,
	std::vector<std::string_view>& results)
{
	// The following code is adapted from: https://stackoverflow.com/a/36301144

	const size_t inputLength = input.length();
	bool foundDoubleQuote = false;
	bool foundSingleQuote = false;
	size_t argumentLength = 0;

	for (size_t i = 0; i < inputLength; i++)
	{
		size_t start = i;
		if (input[i] == '\"')
		{
			foundDoubleQuote = true;
		}
		else if (input[i] == '\'')
		{
			foundSingleQuote = true;
		}

		if (foundDoubleQuote)
		{
			i++;
			start++;

			while (i < inputLength && input[i] != '\"')
			{
				i++;
			}

			if (i < inputLength)
			{
				foundDoubleQuote = false;
			}

			argumentLength = i - start;
			i++;
		}
		else if (foundSingleQuote)
		{
			i++;
			start++;

			while (i < inputLength && input[i] != '\'')
			{
				i++;
			}

			if (i < inputLength)
			{
				foundSingleQuote = false;
			}

			argumentLength = i - start;
			i++;
		}
		else
		{
			while (i < inputLength && input[i] != delimiter)
			{
				i++;
			}
			argumentLength = i - start;
		}

		if (argumentLength > 0)
		{
			results.push_back(input.substr(start, argumentLength));
		}
	}
}
