import {Heading, Text, HStack, Box, IconButton} from "@chakra-ui/react";
import {FiLogOut} from "react-icons/fi";

export default function Header({user, signOut}) {
    return (
        <>
            <Heading size="2xl" colorPalette="blue">
                每日龙
            </Heading>
            <HStack spacing={4} mb={4}>
                <Text>
                    Welcome <Box as="span" fontWeight="bold">{user.username}</Box>
                </Text>
                <IconButton size="sm" onClick={signOut} colorPalette="blue" variant="outline">
                    <FiLogOut/>
                </IconButton>
            </HStack>
        </>
    );
}
